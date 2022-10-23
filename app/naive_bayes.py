from typing import List, Dict, Union
from base64 import b64decode

from app.objects.c_agent import Agent
from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.service.planning_svc import PlanningService

class LogicalPlanner:

    """
    The Naive Bayes Planner makes use of past operation history to run the current operation with priority to links with greatest likelihood of success.

    The NB Planner recieves the following parameters:
        - min_link_data: the minimum number of past runs of a link in existing operational 
        data necessary for planner to utilize its probability of success. Can be custom set by user in 
        \stockpile\data\planners\48e1a882-1606-4910-8f2d-2352eb80cba2.yml, default is 3.

        -  min_probability_link_success: minimum likelihood of success necessary to run a link. Set by user through
        visibility setting in advanced section of operation creation. Calculated as = (99.0% - operation visibility%). Default is 48%

    Algorithm of the planner:
        While there are available links in the operation for live agents, select the links that satisfy minimum operational data settings
        and minimum link probability of success settings and run them in order so that highest likelihood links are run first. Once those
        are exhausted run links that do not satisfy minimum operational data settings in atomic ordering (used by atomic planner). Do not
        ever run links that satisfy operational data restrictions but do not have the necessary minimum link probability of success.
        Run until completed operation or all links have too low likelihood of success.
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
        :param min_link_data: Minimum num runs of link required to use past statistics on it
        :param stopping_conditions:       
        """

        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['bayes_state']
        self.next_bucket = 'bayes_state'   # repeat this bucket until we run out of links
        # holder for Naive Bayes probability data object
        self.matrix_past_links = None
        # min number of datapoints per link for NB calculations, from parameter in planner .yml
        self.min_link_data = min_link_data
        # minimum probability of success needed for link to run, set by user visibility parameter
        self.min_probability_link_success = (99.0-self.operation.visibility)/(100)  # 0-1.0
        print("Minimum REQUIRED PROB OF SUCCESS TO RUN LINK:", self.min_probability_link_success)
        print("NB Planner Initialized")
        self.links_executed = 0

    async def execute(self):
        print("naive_bayes.execute()")
        # execute main state of planner
        await self.planning_svc.execute_planner(self)
    
    async def bayes_state(self):
        """
        Update past data storage if needed then run top priority link for each agent until operation concluded
        """

        print("\nnaive_bayes.bayes_state()")

        # initially build or update the past links df using past and current operation data
        if self.links_executed % 10 == 0:
            print("\nBuilding Past Links DF\n")
            #   await necessary API calls + df building
            # fetch past operation data 
            past_operation_data = await self.planning_svc.get_service('data_svc').locate('operations')
            # build df of link success
            self.matrix_past_links = await self.build_past_links_matrix(past_operation_data)
            self.pretty_print_link_matrix(self.matrix_past_links)

        links_to_use = []

        # Get the first available link for each agent (make sure we maintain the order).
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
            # No more links to run.
            print("El Fin. Operation Concluded.")
            self.next_bucket = None
            self.stopping_condition_met = True

    # Given list of links, returns the link with the highest probability of success
    # that meets user criteria on required data and visibility (AKA risk).
    # If no such link exists then default to atomic ordering planner logic for unknown links
    async def _get_best_link(self, links : List[Link]) -> Union[Link, None]:
        """
        Selects the best link from links or None if all links don't match qualifications. 
        """
        print("_get_best_link")
        print(links)

        # link index (in list) to prob success of link 
        link_to_success_dict = dict()

        # list of links with too little data for backup atomic order planning
        links_insufficient_data = []

        # query probability of each link and store
        for index in range(len(links)):
            # get link at index
            cur_link = links[index]
            # use data necessary to query NB object to build query dictionary
            # NOTE: with link_feature_query_dict can customize which of 16 features to query by
            # current selection of features:
            link_feature_query_dict = {
                "Ability_ID": str(cur_link.ability.ability_id),
                "Link_Facts": self.useful_link_facts(cur_link),
                "Executor_Platform": str(cur_link.executor.platform)
            }
            # fetch probability of success of link with set of features
            print("For link:\n" , link_feature_query_dict)
            prob_success = self.NBLinkSuccessProb(link_feature_query_dict)
            # if returned not enough data return, add to links_insufficient_data list
            # NOTE: also added manual handle that if ability is compress staged directory
            # then store as not enough data and default it to atomic (push to end of execution)
            if prob_success == None or str(cur_link.ability.ability_id) == "300157e5-f4ad-4569-b533-9d1fa0e74d74":
                links_insufficient_data.append(links[index])
                print("Insufficient history of current link")
            # otherwise save probability, by link index in dict
            else:
                print("Link probability of success:", prob_success)
                link_to_success_dict[index] = prob_success
        
        # if some of links have sufficient history
        if len(link_to_success_dict.keys()) > 0:
            # select best link (with highest prob success)
            indexBestLink = max(link_to_success_dict, key=link_to_success_dict.get)
            probSuccessBestLink = link_to_success_dict[indexBestLink]
            if probSuccessBestLink >= self.min_probability_link_success:
                # if a link exists with existing data and high enough prob success, return best success link
                print("Best Link (ID):", links[indexBestLink].ability.ability_id)
                return links[indexBestLink]
            else:
                # all links have too little data or too low prob success
                # if all links have too low prob success
                if  len(links_insufficient_data) == 0:
                    # return No links
                    print("All remaining links have too low probability. Terminating.")
                    return None

        # otherwise for links with too little data perform atomic order planning:
        print("Defaulting link planning to atomic ordering")
        abil_id_to_link = dict()
        for link in links_insufficient_data:
            abil_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(abil_id_to_link.keys())
        for ab_id in self.operation.adversary.atomic_ordering:
            if ab_id in candidate_ids:
                print("Atomic Ordering Link (ID)", ab_id)
                return abil_id_to_link[ab_id]

    def pretty_print_link_matrix(self, matrix_links: List[List]):
        for colval in matrix_links:
            print ('{:4}'.format(str(colval)))

    # param: op_data is past operations list
    async def build_past_links_matrix(self, op_data) -> List[List]:
        """
        Build matrix of links from past operation data with each link as row described by 16 features        
        """
        # Build matrix of Past Links from Operations
        # each row is list of 16 features defining the link
        link_success_matrix = []
        # first row are column names
        link_success_matrix.append([
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
        ])

        # for each operation
        for cur_op in op_data:
            
            # save info about agents into dict for later matching
            agents_dict = {} # key: paw, value: [contact, trusted, privilege, architecture]
            
            # iterate through agents, filling dict with agent/host connection info
            for agent in cur_op.agents:
                agent_paw = agent.paw
                contact_type = agent.contact
                trusted_status = agent.trusted
                privilege = agent.privilege
                architecture = agent.architecture
                agents_dict[agent_paw] = [contact_type, trusted_status, privilege, architecture]
            
            
            # run through each link chain within operation
            for cur_link in cur_op.chain:
            
                # key: link feature, value: link value
                cur_link_dict = {}

                # save relevant global op info
                cur_link_dict["Planner"] = cur_op.planner.name
                cur_link_dict["Obfuscator"] = cur_op.obfuscator
                cur_link_dict["Adversary_ID"] = cur_op.adversary.adversary_id
                cur_link_dict["Adversary_Name"] = cur_op.adversary.name
                
                # save relevant link info
                cur_link_dict["Ability_ID"] = cur_link.ability.ability_id
                cur_link_dict["Status"] = cur_link.status
                decoded_cmd = str(b64decode(cur_link.command).decode('utf-8', errors='ignore').replace('\n', ''))
                cur_link_dict["Command"] = decoded_cmd
                cur_link_dict["Number_Facts"] = len(cur_link.used)
                cur_link_dict["Visibility_Score"] = cur_link.visibility.score
                cur_link_dict["Executor_Platform"] = cur_link.executor.platform
                cur_link_dict["Executor_Name"] = cur_link.executor.name
                
                # save relevant agent related info
                agent_paw = cur_link.paw
                # if agent is in current operation report
                if agent_paw in agents_dict.keys():
                    # save relevant agent/host data
                    contact_type, trusted_status, privilege, architecture = agents_dict[agent_paw]
                    cur_link_dict["Agent_Protocol"] = contact_type
                    cur_link_dict["Trusted_Status"] = trusted_status
                    cur_link_dict["Agent_Privilege"] = privilege
                    cur_link_dict["Host_Architecture"] = architecture
                else: # if agent is not in current agents report
                    # insert None for nonexistant agent data
                    cur_link_dict["Agent_Protocol"] = None
                    cur_link_dict["Trusted_Status"] = None
                    cur_link_dict["Agent_Privilege"] = None
                    cur_link_dict["Host_Architecture"] = None
                    
                # save current usable facts
                cur_link_dict["Link_Facts"] = self.useful_link_facts(cur_link)        

                # create link list from dict 
                cur_link_list = [
                    cur_link_dict["Status"],
                    cur_link_dict["Ability_ID"], 
                    cur_link_dict["Link_Facts"], 
                    cur_link_dict["Planner"],
                    cur_link_dict["Obfuscator"],
                    cur_link_dict["Adversary_ID"],
                    cur_link_dict["Adversary_Name"],
                    cur_link_dict["Command"],
                    cur_link_dict["Number_Facts"],
                    cur_link_dict["Visibility_Score"],
                    cur_link_dict["Executor_Platform"],
                    cur_link_dict["Executor_Name"],
                    cur_link_dict["Agent_Protocol"],
                    cur_link_dict["Trusted_Status"],
                    cur_link_dict["Agent_Privilege"],
                    cur_link_dict["Host_Architecture"]
                ]
                link_success_matrix.append(cur_link_list)
        return link_success_matrix

    # helper method for nb model class and nb planner that accepts a link object
    # and returns the usable facts from the link in a dict
    def useful_link_facts(self, cur_link : Link) -> Dict[str, str]:
        """
        :param cur_link: link object for which to select useful (generalizable) facts
        """
        cur_used_global_facts = {} # key: trait, val: value    
        # used facts of link
        if(len(cur_link.used) > 0):
            # iterate through facts
            for used_fact in cur_link.used:
                useful_fact = True
                # check if fact unique to host through excluding unique fact types
                if str(used_fact.trait).startswith("host."):
                    useful_fact = False
                if str(used_fact.trait).startswith("remote."):
                    useful_fact = False
                if str(used_fact.trait).startswith("file.last."):
                    useful_fact = False
                if str(used_fact.trait).startswith("domain.user."):
                    useful_fact = False
                if useful_fact:
                    # save fact
                    cur_used_global_facts[str(used_fact.trait)] = str(used_fact.value)
        # save current usable facts
        return cur_used_global_facts

    # query param1 matrix according to features in param2 dict
    # used by probability functions to return relevant portions of matrix
    def query_link_matrix(self, cur_link_success_matrix : List[List], feature_query_dict : Dict) -> List[List]:
        """
        Query parameter link matrix for links containing all features and values in feature_query_dict 
        """

        # creat dict - maps matrix column name to matrix column index
        col_name_to_index = {}
        for index in range(len(cur_link_success_matrix[0])):
            col_name_to_index[cur_link_success_matrix[0][index]] = index

        # output - queried link obj (matrix) with feature labels (columns)
        queried_link_matrix = [cur_link_success_matrix[0]]

        # iterate through matrix of links
        for row_index in range(1, len(cur_link_success_matrix)):
            # get link from matrix
            cur_link = cur_link_success_matrix[row_index]
            # passed conditions bool
            pass_conditions = True
            # query by each features, value in feature_query_dict
            for feat_name, feat_value in feature_query_dict.items():
                feat_index = col_name_to_index[feat_name]
                if feat_name == "Link_Facts":
                    cur_facts_dict = cur_link[feat_index]
                    # query by link_facts (stored in dict)
                    for req_fact_type, req_fact_val in feature_query_dict["Link_Facts"].items():
                        # check that current link contains required fact type and required fact value
                        if req_fact_type not in cur_facts_dict or str(cur_facts_dict[req_fact_type]) != str(req_fact_val):
                            pass_conditions = False
                else:
                    if str(cur_link[feat_index]) != str(feat_value):
                        pass_conditions = False
            if pass_conditions:
                queried_link_matrix.append(cur_link)
        return queried_link_matrix

    # NB Link Success Probability
    # Calculates Prob(Status=0 | features in feature_query_dict)
    def NBLinkSuccessProb(self, feature_query_dict : Dict) -> Union[float, None]: 
        """
        Calculates Naive Bayes probability for a link with features and values in feature_query_dict running succesfully.
        """
        link_success_matrix = self.matrix_past_links

        num_total_past_links = len(link_success_matrix)-1
        # return None if there is 0 past link data
        if num_total_past_links == 0:
            return None

        # P(A)    Probability Status == 0
        status_0_matrix = self.query_link_matrix(link_success_matrix, {"Status" : 0})
        status_0_past_links = len(status_0_matrix)-1
        prob_a = status_0_past_links/num_total_past_links 
                                    
        # P(B)    Probability of current features
        current_feature_matrix = self.query_link_matrix(link_success_matrix, feature_query_dict)
        num_current_feature_links = len(current_feature_matrix)-1
        # if less items than user required params then return None
        if num_current_feature_links < self.min_link_data:
            return None

        prob_b = num_current_feature_links/num_total_past_links 
        
        # P(B|A)    Probability of current features in Status == 0 DF
        current_feature_status_0_matrix = self.query_link_matrix(status_0_matrix, feature_query_dict)
        current_feature_status_0_links = len(current_feature_status_0_matrix)-1
        prob_b_given_a = current_feature_status_0_links / status_0_past_links
        
        # NB Formula
        # P(A|B) = (P(B|A)*P(A))/P(B)
        return ((prob_b_given_a * prob_a)/prob_b)
