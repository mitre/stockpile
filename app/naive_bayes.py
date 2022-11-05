from typing import List, Dict, Union
from base64 import b64decode

from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.service.planning_svc import PlanningService

class LogicalPlanner:

    """
    The Naive Bayes Planner makes use of past operational history to run the current operation with priority to links with greatest likelihood of success.
    With sufficient local data, NB planner runs all operations in order of most to least effective links, while dropping links with insufficient likelihood of success.

    The NB Planner recieves the following parameters:
        - min_link_data: the minimum number of past runs of a link in existing operational 
        data necessary for planner to utilize its probability of success. Can be custom set by user in 
        \stockpile\data\planners\48e1a882-1606-4910-8f2d-2352eb80cba2.yml, default is 3.

        -  min_probability_link_success: minimum calculated likelihood of success necessary to run a link. Set by user through
        visibility setting in advanced section of operation creation. Calculated as = (99.0% - operation visibility%). Default is 48%

    Algorithm of the planner:
        -While there are available links in the operation for live agents:
            -If there are links that satisfy minimum operational data settings and minimum link probability of success settings:
                -Execute them in order of likelihood of success (high to low)
            -Run all remaining links with insufficient past operational data in atomic ordering (used by atomic planner)
            -Drop any links that with sufficient past data but insufficient calculated probability of success
        -Terminate when out of links or all links have too low likelihood of success.
    """

    def __init__(
        self, 
        operation: Operation, 
        planning_svc: PlanningService, 
        min_link_data : int, 
        stopping_conditions: List[Fact] = ()
    ):
        """
        :param operation:
        :param planning_svc:
        :param min_link_data: Minimum number runs of link required to use past statistics on it
        :param stopping_conditions:       
        """
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['bayes_state']
        self.next_bucket = 'bayes_state'
        self.matrix_past_link_data = None
        self.min_link_data = min_link_data
        self.min_probability_link_success = (99.0-self.operation.visibility)/(100)
        print("NB Planner Initialized")
        self.links_executed = 0

    async def execute(self):
        print("naive_bayes.execute()")
        await self.planning_svc.execute_planner(self)
    
    async def bayes_state(self):
        """
        Update past operational data matrix if needed then run top priority link for each agent until operation concluded
        """
        print("\nnaive_bayes.bayes_state()")

        if self.links_executed % 10 == 0:
            print("\nBuilding Past Links DF\n")
            past_operation_data = await self.planning_svc.get_service('data_svc').locate('operations')
            self.matrix_past_link_data = await self._build_past_links_matrix(past_operation_data)
            self.pretty_print_link_matrix(self.matrix_past_link_data)

        links_to_use = []

        for agent in self.operation.agents:
            possible_agent_links = await self.planning_svc.get_links(operation=self.operation, agent=agent)
            next_link = await self._get_best_link(possible_agent_links)
            if next_link:
                links_to_use.append(await self.operation.apply(next_link))
        if links_to_use:
            # Each agent will run the next available step.
            await self.operation.wait_for_links_completion(links_to_use)
            self.links_executed += 1
        else:
            print("El Fin. Operation Concluded.")
            self.next_bucket = None
            self.stopping_condition_met = True

    async def _get_best_link(self, links : List[Link]) -> Union[Link, None]:
        """
        Selects the best link from links or None if all links don't match qualifications. 

        :param links: list of links that agent could execute
        """
        print("_get_best_link")
        print(links)

        dict_link_index_to_prob_success = dict()
        links_insufficient_data = []

        for index in range(len(links)):
            cur_link = links[index]
            # NOTE: with link_feature_query_dict can customize which of 16 features to query by
            # current selection of features:
            link_feature_query_dict = {
                "Ability_ID": str(cur_link.ability.ability_id),
                "Link_Facts": self._get_useful_link_facts(cur_link),
                "Executor_Platform": str(cur_link.executor.platform)
            }

            print("For link:\n" , link_feature_query_dict)
            prob_success_cur_link = self._get_NB_link_success_probability(link_feature_query_dict)

            if prob_success_cur_link == None or str(cur_link.ability.ability_id) == "300157e5-f4ad-4569-b533-9d1fa0e74d74":
                # Added manual handle that if ability is compress staged directory then store as 
                # not enough data and default it to atomic (push to end of execution) for better operation ordering
                links_insufficient_data.append(cur_link)
                print("Insufficient history of current link")
            else:
                print("Link probability of success:", prob_success_cur_link)
                dict_link_index_to_prob_success[index] = prob_success_cur_link
        
        if len(dict_link_index_to_prob_success.keys()) > 0:
            indexBestLink = max(dict_link_index_to_prob_success, key=dict_link_index_to_prob_success.get)
            probSuccessBestLink = dict_link_index_to_prob_success[indexBestLink]
            if probSuccessBestLink >= self.min_probability_link_success:
                print("Best Link (ID):", links[indexBestLink].ability.ability_id)
                return links[indexBestLink]
            else:
                if  len(links_insufficient_data) == 0:
                    print("All remaining links have too low probability. Terminating.")
                    return None

        # backup atomic ordering 
        print("Defaulting link planning to atomic ordering")
        abil_id_to_link = dict()
        for link in links_insufficient_data:
            abil_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(abil_id_to_link.keys())
        for ab_id in self.operation.adversary.atomic_ordering:
            if ab_id in candidate_ids:
                print("Atomic Ordering Link (ID)", ab_id)
                return abil_id_to_link[ab_id]

    # TODO: remove with the other print statements
    def pretty_print_link_matrix(self, matrix_links: List[List]):
        for colval in matrix_links:
            print ('{:4}'.format(str(colval)))

    async def _build_past_links_matrix(self, op_data) -> List[List]:
        """
        Build matrix of links from past operation data with each link as row described by 16 features        

        :param op_data: local past operational data object
        """
        matrix_link_data = []
        feature_names = [
            "Status",
            "Ability_ID", 
            "Link_Facts", 
            "Planner",
            "Obfuscator",
            "Adversary_ID",
            "Adversary_Name",
            "Command",
            "Number_Facts",
            "Visibility_Score",
            "Executor_Platform",
            "Executor_Name",
            "Agent_Protocol",
            "Trusted_Status",
            "Agent_Privilege",
            "Host_Architecture"
        ]
        # first row are column names
        matrix_link_data.append(feature_names)

        for cur_operation in op_data:         
            dict_agent_paw_to_info = {}
            for agent in cur_operation.agents:
                agent_paw = agent.paw
                contact_type = agent.contact
                trusted_status = agent.trusted
                privilege = agent.privilege
                architecture = agent.architecture
                dict_agent_paw_to_info[agent_paw] = [contact_type, trusted_status, privilege, architecture]           
            
            for cur_link in cur_operation.chain:
            
                dict_cur_link_feature_to_val = {}
                dict_cur_link_feature_to_val["Planner"] = cur_operation.planner.name
                dict_cur_link_feature_to_val["Obfuscator"] = cur_operation.obfuscator
                dict_cur_link_feature_to_val["Adversary_ID"] = cur_operation.adversary.adversary_id
                dict_cur_link_feature_to_val["Adversary_Name"] = cur_operation.adversary.name
                dict_cur_link_feature_to_val["Ability_ID"] = cur_link.ability.ability_id
                dict_cur_link_feature_to_val["Status"] = cur_link.status
                decoded_cmd = str(b64decode(cur_link.command).decode('utf-8', errors='ignore').replace('\n', ''))
                dict_cur_link_feature_to_val["Command"] = decoded_cmd
                dict_cur_link_feature_to_val["Number_Facts"] = len(cur_link.used)
                dict_cur_link_feature_to_val["Visibility_Score"] = cur_link.visibility.score
                dict_cur_link_feature_to_val["Executor_Platform"] = cur_link.executor.platform
                dict_cur_link_feature_to_val["Executor_Name"] = cur_link.executor.name
                
                agent_paw = cur_link.paw
                if agent_paw in dict_agent_paw_to_info.keys():
                    contact_type, trusted_status, privilege, architecture = dict_agent_paw_to_info[agent_paw]
                    dict_cur_link_feature_to_val["Agent_Protocol"] = contact_type
                    dict_cur_link_feature_to_val["Trusted_Status"] = trusted_status
                    dict_cur_link_feature_to_val["Agent_Privilege"] = privilege
                    dict_cur_link_feature_to_val["Host_Architecture"] = architecture
                else:
                    dict_cur_link_feature_to_val["Agent_Protocol"] = None
                    dict_cur_link_feature_to_val["Trusted_Status"] = None
                    dict_cur_link_feature_to_val["Agent_Privilege"] = None
                    dict_cur_link_feature_to_val["Host_Architecture"] = None

                dict_cur_link_feature_to_val["Link_Facts"] = self._get_useful_link_facts(cur_link)

                list_cur_link_row = [
                    dict_cur_link_feature_to_val["Status"],
                    dict_cur_link_feature_to_val["Ability_ID"], 
                    dict_cur_link_feature_to_val["Link_Facts"], 
                    dict_cur_link_feature_to_val["Planner"],
                    dict_cur_link_feature_to_val["Obfuscator"],
                    dict_cur_link_feature_to_val["Adversary_ID"],
                    dict_cur_link_feature_to_val["Adversary_Name"],
                    dict_cur_link_feature_to_val["Command"],
                    dict_cur_link_feature_to_val["Number_Facts"],
                    dict_cur_link_feature_to_val["Visibility_Score"],
                    dict_cur_link_feature_to_val["Executor_Platform"],
                    dict_cur_link_feature_to_val["Executor_Name"],
                    dict_cur_link_feature_to_val["Agent_Protocol"],
                    dict_cur_link_feature_to_val["Trusted_Status"],
                    dict_cur_link_feature_to_val["Agent_Privilege"],
                    dict_cur_link_feature_to_val["Host_Architecture"]
                ]
                matrix_link_data.append(list_cur_link_row)
        return matrix_link_data

    def _get_useful_link_facts(self, cur_link : Link) -> Dict[str, str]:
        """
        selects generalizable facts from link object for data querying
        """
        dict_useful_facts_trait_to_val = {}
        if(len(cur_link.used) > 0):
            for used_fact in cur_link.used:
                # exclude fact types that are unique to a host
                if str(used_fact.trait).startswith(("host.", "remote.", "file.last.", "domain.user.")) == False:
                    dict_useful_facts_trait_to_val[str(used_fact.trait)] = str(used_fact.value)
        return dict_useful_facts_trait_to_val

    def _query_link_matrix(self, cur_matrix_link_data : List[List], feature_query_dict : Dict) -> List[List]:
        """
        Query link matrix for links containing specific features and values and 
        return new matrix composed of column names row and the link rows containing right feat and val

        :param cur_matrix_link_data: link matrix that will be queried
        :param feature_query_dict: dict of {feature_names: feature_values} that cur_matrix_link_data will be queried by
        """

        dict_col_name_to_col_index = {}
        list_col_names = cur_matrix_link_data[0]
        for index_feature_names in range(len(list_col_names)):
            dict_col_name_to_col_index[list_col_names[index_feature_names]] = index_feature_names

        queried_link_matrix = [list_col_names]
        for row_index in range(1, len(cur_matrix_link_data)):
            cur_link = cur_matrix_link_data[row_index]
            row_passes_conditions = True
            for feat_name, feat_value in feature_query_dict.items():
                feat_index = dict_col_name_to_col_index[feat_name]
                if feat_name == "Link_Facts":
                    cur_facts_dict = cur_link[feat_index]
                    for req_fact_type, req_fact_val in feature_query_dict["Link_Facts"].items():
                        # check that current link contains required fact type and required fact value
                        if req_fact_type not in cur_facts_dict or str(cur_facts_dict[req_fact_type]) != str(req_fact_val):
                            row_passes_conditions = False
                else:
                    if str(cur_link[feat_index]) != str(feat_value):
                        row_passes_conditions = False
            if row_passes_conditions:
                queried_link_matrix.append(cur_link)
        return queried_link_matrix

    def _get_NB_link_success_probability(self, feature_query_dict : Dict) -> Union[float, None]: 
        """
        Calculates Naive Bayes probability for a link (with features and values from feature_query_dict) executing succesfully.
        """
        matrix_link_data = self.matrix_past_link_data
        num_total_past_links = len(matrix_link_data)-1
        if num_total_past_links == 0:
            return None
        status_0_matrix = self._query_link_matrix(matrix_link_data, {"Status" : 0})
        status_0_past_links = len(status_0_matrix)-1
        prob_a = status_0_past_links/num_total_past_links                                   
        current_feature_matrix = self._query_link_matrix(matrix_link_data, feature_query_dict)
        num_current_feature_links = len(current_feature_matrix)-1
        # if less links with these features than user required then return None
        if num_current_feature_links < self.min_link_data:
            return None
        prob_b = num_current_feature_links/num_total_past_links 
        current_feature_status_0_matrix = self._query_link_matrix(status_0_matrix, feature_query_dict)
        current_feature_status_0_links = len(current_feature_status_0_matrix)-1
        prob_b_given_a = current_feature_status_0_links / status_0_past_links
        return ((prob_b_given_a * prob_a)/prob_b)
