from base64 import b64decode
from typing import List, Dict

from app.service.data_svc import DataService
from app.objects.secondclass.c_link import Link

class NBLinkProbabilities:

    def __init__(self, data_svc_obj : DataService):
        # self.operations_matrix stores past links for probability functions  
        self.operations_matrix = None
        self.my_data_svc = data_svc_obj

    def pretty_print_link_matrix(self, matrix_links: List[List]):
        for colval in matrix_links:
            print ('{:4}'.format(str(colval)))

    async def startup_operations(self):
        """
        Fetches past operational data and builds matrix of past link data from it.
        """
        # fetch past operation data 
        operation_data = await self.fetch_operation_data()
        # build df of link success
        self.operations_matrix = await self.build_operations_df(operation_data)
        self.pretty_print_link_matrix(self.operations_matrix)
        return None

    async def fetch_operation_data(self):
        # fetch Data SVC past operation data")
        return await self.my_data_svc.locate('operations')

    # param: op_data is past operations list
    async def build_operations_df(self, op_data):
        
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
    def useful_link_facts(self, cur_link : Link):
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
    def query_link_matrix(self, cur_link_success_matrix : List[List], feature_query_dict : Dict):
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

    # Basic Success Probability function, returns % of links with features from feature_query_dict that are succesful
    def BaseSuccessProb(self, feature_query_dict : Dict):
        query_matrix = self.query_link_matrix(self.link_success_matrix, feature_query_dict) # query matrix for features
        # if there is no such features
        if len(query_matrix) <= 1:
                return 0.0
        # otherwise return percentage with status == 0:
        number_success = 0.0
        for rowIndex in range(1, len(query_matrix)):
                if query_matrix[rowIndex][0] == 0:
                        number_success +=1.0
        return (100.0 * (number_success / (len(query_matrix)-1))) 


    # NB Link Success Probability
    # Calculates Prob(Status=0 | features in feature_query_dict)
    def NBLinkSuccessProb(self, feature_query_dict : Dict, min_link_data : int): 
        link_success_matrix = self.operations_matrix

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
        if num_current_feature_links < min_link_data:
            return None

        prob_b = num_current_feature_links/num_total_past_links 
        
        # P(B|A)    Probability of current features in Status == 0 DF
        current_feature_status_0_matrix = self.query_link_matrix(status_0_matrix, feature_query_dict)
        current_feature_status_0_links = len(current_feature_status_0_matrix)-1
        prob_b_given_a = current_feature_status_0_links / status_0_past_links
        
        # NB Formula
        # P(A|B) = (P(B|A)*P(A))/P(B)
        return ((prob_b_given_a * prob_a)/prob_b)
        
# Example Call:
# BaseSuccessProb({"Ability_ID": "90c2efaa-8205-480d-8bb6-61d90dbaf81b", "Link_Facts":{'file.sensitive.extension': 'wav'}, "Executor_Platform": "windows"})
# Example Call:
# NBLinkSuccessProb({"Ability_ID": "90c2efaa-8205-480d-8bb6-61d90dbaf81b", "Link_Facts":{'file.sensitive.extension': 'wav'}, "Executor_Platform": "windows"})