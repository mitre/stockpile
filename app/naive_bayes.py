from typing import List, Dict, Union
from base64 import b64decode
from app.objects.c_operation import Operation
from app.objects.secondclass.c_link import Link
from app.objects.secondclass.c_fact import Fact
from app.service.planning_svc import PlanningService

# update planner's operational data after how many links
UPDATE_AFTER_LINKS = 10
# Names of features collected per link from operational data
FEATURE_NAMES = [
    "Status",  "Ability_ID",  "Link_Facts",  "Planner",  "Obfuscator",
    "Adversary_ID",  "Adversary_Name",  "Command",  "Number_Facts",
    "Visibility_Score",  "Executor_Platform",  "Executor_Name",
    "Agent_Protocol",  "Trusted_Status",  "Agent_Privilege",  "Host_Architecture"
]
HOST_SPECIFIC_FACT_TRAITS = ("host.", "remote.", "file.last.", "domain.user.")

class LogicalPlanner:
    """
    The Naive Bayes Planner utilizes past operational history to execute operations while prioritizing likelihood of link success.
    With sufficient local data, NB planner runs all operations in order of most to least effective links, while dropping links with insufficient likelihood of success.

    The NB Planner recieves the following parameters:
        - min_link_data: the minimum number of past runs of a link in existing past operational 
        data necessary for planner to utilize its probability of success. Can be custom set by user in 
        \stockpile\data\planners\48e1a882-1606-4910-8f2d-2352eb80cba2.yml, default is 3.

        - decision_logging: Boolean indicating whether planner should log link selection logic
        in DEBUG level system output. Defaults to False, can also be changed in .yml config.

        - delay_execution_links: list of link ids whose execution should be pushed back to atomic ordering
        and treated as insufficient data to improve operation ordering. Set in config.

        -  min_prob_link_success: minimum calculated likelihood of success necessary to run a link. Set by user through
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
        min_link_data: int, 
        decision_logging: bool,
        delay_execution_links: List[str],
        stopping_conditions: List[Fact] = ()
    ):
        """
        :param operation:
        :param planning_svc:
        :param min_link_data: Minimum number runs of link required to use past statistics on it
        :param decision_logging: Whether planner should log link selection logic
        :param delay_execution_links: link ids whose execution should be delayed to backup
        :param stopping_conditions:       
        """
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['bayes_state']
        self.next_bucket = 'bayes_state'
        self.matrix_past_links = None
        self.min_link_data = min_link_data
        self.decision_logging = decision_logging
        self.delay_execution_links = delay_execution_links
        self.min_prob_link_success = (99.0-self.operation.visibility)/(100)
        self.links_executed = 0
        if self.decision_logging:
            self.planning_svc.log.debug("Operation started")   

    async def execute(self):
        await self.planning_svc.execute_planner(self)
    
    async def bayes_state(self):
        """
        Update past operational data matrix if needed then run top priority link for each agent until operation concluded
        """
        if self.links_executed % UPDATE_AFTER_LINKS == 0:
            past_operation_data = await self.planning_svc.get_service('data_svc').locate('operations')
            self.matrix_past_links = await self._build_past_links_matrix(past_operation_data)

        links_to_use = []
        for agent in self.operation.agents:
            possible_agent_links = await self.planning_svc.get_links(operation=self.operation, agent=agent)
            next_link = await self._get_best_link(possible_agent_links)
            if next_link:
                links_to_use.append(await self.operation.apply(next_link))
        if links_to_use:
            # Each agent will run the next available step.
            await self.operation.wait_for_links_completion(links_to_use)
            self.links_executed += len(links_to_use)
        else:
            if self.decision_logging:
                self.planning_svc.log.debug("Operation concluded")
            self.next_bucket = None
            self.stopping_condition_met = True

    async def _get_best_link(self, links : List[Link]) -> Union[Link, None]:
        """
        Selects the best link from links or None if all links don't match qualifications. 

        :param links: list of links that agent could execute
        """
        dict_link_index_to_prob_success = dict()
        dict_link_index_to_num_observations = dict()
        links_insufficient_data = []

        for index, cur_link in enumerate(links): 
            # NOTE: link_query_features allows customizing which of FEATURE_NAMES to query by
            # current selection of features with broad scope:
            link_query_features = {
                "Ability_ID": str(cur_link.ability.ability_id),
                "Link_Facts": self._get_useful_facts(cur_link),
                "Executor_Platform": str(cur_link.executor.platform)
            }
            prob_link_success, num_link_observations = self._get_link_success_probability(link_query_features)
            if prob_link_success == None or str(cur_link.ability.ability_id) in self.delay_execution_links:
                # config delayed links are also treated as insufficient data
                links_insufficient_data.append(cur_link)
            else:
                dict_link_index_to_prob_success[index] = prob_link_success
                dict_link_index_to_num_observations[index] = num_link_observations

        if len(dict_link_index_to_prob_success.keys()) > 0:
            index_best_link = max(dict_link_index_to_prob_success, key=dict_link_index_to_prob_success.get)
            prob_success_best_link = dict_link_index_to_prob_success[index_best_link]
            if prob_success_best_link >= self.min_prob_link_success:
                if self.decision_logging:
                    self.planning_svc.log.debug("Best link selected with probability of success " + "{:.2f}".format(prob_success_best_link*100)
                    + "%" + " based on " + str(dict_link_index_to_num_observations[index_best_link]) +" observations")
                return links[index_best_link]
            else:
                if self.decision_logging:
                    self.planning_svc.log.debug("Skipping " + str(len(dict_link_index_to_prob_success.keys()))
                    + " link(s) with insufficient likelihood of success")
        return self._backup_atomic_ordering(links_insufficient_data)

    def _backup_atomic_ordering(self, links_insufficient_data : List[Link]) ->  Union[Link, None]:
        """
        Select a link based on atomic ordering        

        :param links_insufficient_data: links with insufficient data for probability selection
        """ 
        abil_id_to_link = dict()
        for link in links_insufficient_data:
            abil_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(abil_id_to_link.keys())
        for ab_id in self.operation.adversary.atomic_ordering:
            if ab_id in candidate_ids:
                if self.decision_logging:
                    self.planning_svc.log.debug("Link selected with backup atomic ordering")
                return abil_id_to_link[ab_id]

    async def _build_past_links_matrix(self, op_data : List[Operation]) -> List[List]:
        """
        Build matrix of links from past operation data with each link as row described by 16 features        

        :param op_data: local past operational data object
        """
        matrix_link_data = []

        for cur_operation in op_data:         
            dict_agent_paw_to_info = {}
            for agent in cur_operation.agents:
                dict_agent_paw_to_info[agent.paw] = [agent.contact, agent.trusted, agent.privilege, agent.architecture]           
            
            for cur_link in cur_operation.chain:
                dict_link_features = {}
                dict_link_features["Planner"] = cur_operation.planner.name
                dict_link_features["Obfuscator"] = cur_operation.obfuscator
                dict_link_features["Adversary_ID"] = cur_operation.adversary.adversary_id
                dict_link_features["Adversary_Name"] = cur_operation.adversary.name
                dict_link_features["Ability_ID"] = cur_link.ability.ability_id
                dict_link_features["Status"] = cur_link.status
                dict_link_features["Command"] = str(b64decode(cur_link.command).decode('utf-8', errors='ignore').replace('\n', ''))
                dict_link_features["Number_Facts"] = len(cur_link.used)
                dict_link_features["Visibility_Score"] = cur_link.visibility.score
                dict_link_features["Executor_Platform"] = cur_link.executor.platform
                dict_link_features["Executor_Name"] = cur_link.executor.name
                
                agent_paw = cur_link.paw
                if agent_paw in dict_agent_paw_to_info.keys():
                    contact_type, trusted_status, privilege, architecture = dict_agent_paw_to_info[agent_paw]
                    dict_link_features["Agent_Protocol"] = contact_type
                    dict_link_features["Trusted_Status"] = trusted_status
                    dict_link_features["Agent_Privilege"] = privilege
                    dict_link_features["Host_Architecture"] = architecture
                else:
                    dict_link_features["Agent_Protocol"] = None
                    dict_link_features["Trusted_Status"] = None
                    dict_link_features["Agent_Privilege"] = None
                    dict_link_features["Host_Architecture"] = None

                dict_link_features["Link_Facts"] = self._get_useful_facts(cur_link)

                link_row = [dict_link_features[feature] for feature in FEATURE_NAMES]
                matrix_link_data.append(link_row)
        return matrix_link_data

    def _get_useful_facts(self, cur_link : Link) -> Dict[str, str]:
        """
        Selects generalizable facts from link object for data querying
        """
        useful_facts = {}
        if len(cur_link.used) > 0:
            for used_fact in cur_link.used:
                # exclude fact types that are unique to a specific host
                if str(used_fact.trait).startswith(HOST_SPECIFIC_FACT_TRAITS) == False:
                    useful_facts[str(used_fact.trait)] = str(used_fact.value)
        return useful_facts

    def _query_link_matrix(self, matrix_link_data : List[List], query_features : Dict) -> List[List]:
        """
        Query link matrix for links containing specific features and values and 
        return new matrix composed of column names row and the link rows containing right feat and val

        :param matrix_link_data: link matrix that will be queried
        :param query_features: dict of {feature_names: values} that matrix_link_data will be queried by
        """
        queried_link_matrix = []
        for cur_link in matrix_link_data:
            row_passes_conditions = True
            for feat_name, feat_value in query_features.items():
                feat_index = FEATURE_NAMES.index(feat_name)
                if feat_name == "Link_Facts":
                    cur_facts_dict = cur_link[feat_index]
                    for req_fact_type, req_fact_val in query_features["Link_Facts"].items():
                        # check that current link contains required fact type and required fact value
                        if req_fact_type not in cur_facts_dict or str(cur_facts_dict[req_fact_type]) != str(req_fact_val):
                            row_passes_conditions = False
                else:
                    if str(cur_link[feat_index]) != str(feat_value):
                        row_passes_conditions = False
            if row_passes_conditions:
                queried_link_matrix.append(cur_link)
        return queried_link_matrix

    def _get_link_success_probability(self, query_features : Dict): 
        """
        Calculates Naive Bayes probability for a link (with features and values from query_features) executing successfully.
        Returns success probability, and number of link observations in dataset.
        """
        num_total_links = len(self.matrix_past_links)
        if num_total_links == 0:
            return None, 0
        status_0_matrix = self._query_link_matrix(self.matrix_past_links, {"Status" : 0})
        num_status_0_links = len(status_0_matrix)
        prob_a = num_status_0_links/num_total_links                                   
        query_feat_matrix = self._query_link_matrix(self.matrix_past_links, query_features)
        num_query_links = len(query_feat_matrix)
        # if less links with these features than user required to use probability then return None
        if num_query_links < self.min_link_data:
            return None, num_query_links
        prob_b = num_query_links/num_total_links 
        query_feat_status_0_matrix = self._query_link_matrix(status_0_matrix, query_features)
        num_query_feat_status_0_links = len(query_feat_status_0_matrix)
        prob_b_given_a = num_query_feat_status_0_links / num_status_0_links
        return ((prob_b_given_a * prob_a)/prob_b), num_query_links