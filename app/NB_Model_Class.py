import requests
import pandas
import base64


class NBLinkProbabilities:


    def __init__(self, data_svc_obj):
        # NOTE: accept system data here from planner
        # self.operation_data = self.fetch_API_operation_data()
        # self.operations_df = self.build_operations_df(self.operation_data)
        # NOTE: self.operations_df is link_success_df used in probability functions  
        self.operation_data = None
        self.operations_df = None
        self.my_data_svc = data_svc_obj

    async def startup_operations(self):
        self.operation_data = await self.fetch_operation_data()
        print("Building Link DF")
        self.operations_df = await self.build_operations_df(self.operation_data)
        print("Startup Finished")
        return None

    async def fetch_operation_data(self):
        print("Fetching Data SVC Operation Data")
        return await self.my_data_svc.locate('operations')


    # DEPRECATED
    # API Fetch of Operation Data works standalone or in Notebook, but causing issues
    # when linked to Caldera planner implementation
    async def fetch_API_operation_data(self):
        # Create REST API calls to server to fetch operational data and current system conditions, store in df.
        # fetch past operational data
        op_url = 'http://localhost:8888/api/v2/operations'
        headers = {'Accept': 'application/json', 'KEY' :'ADMIN123'}

        op_response = await requests.get(op_url, headers=headers)
        
        op_data = pandas.DataFrame(op_response.json())
        op_data = op_data.reset_index()  # make sure indexes pair with number of rows
        return op_data

    def fetch_cur_agent_data(self):
        # fetch current system conditions of active agent
        # NOTE: using first trusted agent by default, replace with valid agent(s) for operation + alive and trusted
        agents_url = 'http://localhost:8888/api/v2/agents'
        agents_response = requests.get(agents_url, headers=headers)
        agents_list = agents_response.json()
        # select trusted agent
        agent_selected = None
        for agent in agents_list:
            if agent["trusted"] == True:
                # TODO: insert check for whether agent is alive
                agent_selected = agent

        if agent_selected == None:
            print("FAILURE TO FIND AGENT")
        else: 
            print("Operation + Agent Data Fetched")
        # Agent data is for simulation of live conditions of agent for calculating link probabilities.


    # param: op_data is past operations list
    async def build_operations_df(self, op_data):
        print("Past Operations Obj:")
        print(op_data)


        ## Build DF of Past Links from Operations
        # store link info in lists, where each item corresponds to link at index
        # same index in each list gives all relevant info on link
        # later convert to df, for efficiency
        statuses = []
        ability_ids = []
        usable_facts = [] # contains lists of fact dicts with 0 or more items
        planners = []
        agent_protocols = []           
        agent_trusted_statuses = []
        agent_architectures = []
        agent_privileges = []
        obfuscators = []
        adversary_ids = []
        adversary_names = []
        commands = []
        num_facts_used = []
        visibility_scores = []
        executor_platforms = []  # platform on which agent executes it
        executor_names = [] # name of terminal on which agent running
        # NOTE: see useful_features.odt for analysis of useful components.

        # for each operation
        for cur_op in op_data:
            
            # save info about agents into dict for later matching
            agents_dict = {} # key: paw, value: [contact, trusted, privilege, architecture]
            
            # iterate through agents, filling dict with agent/host connection info
            for agent in cur_op["host_group"]:
                agent_paw = agent["paw"]
                contact_type = agent["contact"]
                trusted_status = agent["trusted"]
                privilege = agent["privilege"]
                architecture = agent["architecture"]
                agents_dict[agent_paw] = [contact_type, trusted_status, privilege, architecture]
            
            
            # run through each link chain within operation
            for cur_link in cur_op["chain"]:
            
                # save relevant global op info
                planners.append(cur_op["planner"]["name"])
                obfuscators.append(cur_op["obfuscator"])
                adversary_ids.append(cur_op["adversary"]["adversary_id"])
                adversary_names.append(cur_op["adversary"]["name"])
                
                # save relevant link info
                ability_ids.append(cur_link["ability"]["ability_id"])
                statuses.append(cur_link["status"])
                command_str = str(base64.b64decode(cur_link["command"]))
                command_str = command_str[2:len(command_str)-1] # correctly format
                commands.append(command_str)
                num_facts_used.append(len(cur_link["used"]))
                visibility_scores.append(cur_link["visibility"]["score"])
                executor_platforms.append(cur_link["executor"]["platform"])
                executor_names.append(cur_link["executor"]["name"])
                
                # save relevant agent related info
                agent_paw = cur_link["paw"]
                # if agent is in current operation report
                if agent_paw in agents_dict.keys():
                    # save relevant agent/host data
                    contact_type, trusted_status, privilege, architecture = agents_dict[agent_paw]
                    agent_protocols.append(contact_type)
                    agent_trusted_statuses.append(trusted_status)
                    agent_privileges.append(privilege)
                    agent_architectures.append(architecture)
                else: # if agent is not in current agents report (currently, 5/733 links)
                    # insert None for nonexistant agent data
                    agent_protocols.append(None)
                    agent_trusted_statuses.append(None)
                    agent_privileges.append(None)
                    agent_architectures.append(None)
                    
                
                cur_used_global_facts = {} # key: trait, val: value    
                
                # used facts of link
                if(len(cur_link["used"]) > 0):
                    
                    # iterate through facts
                    for used_fact in cur_link["used"]:
                        useful_fact = True
                        # check if fact unique to host through excluding unique fact types
                        if used_fact["trait"].startswith("host."):
                            useful_fact = False
                        if used_fact["trait"].startswith("remote."):
                            useful_fact = False
                        if used_fact["trait"].startswith("file.last."):
                            useful_fact = False
                        if used_fact["trait"].startswith("domain.user."):
                            useful_fact = False
                        
                        if useful_fact:
                            # save fact
                            cur_used_global_facts[str(used_fact["trait"])] = str(used_fact["value"])

                # save current usable facts
                usable_facts.append(cur_used_global_facts)        
                

        # create link success df from lists of data
        data_link_success = {
            "Status" : statuses,
            "Ability_ID" : ability_ids, 
            "Link_Facts" : usable_facts, 
            "Planner" : planners,
            "Obfuscator" : obfuscators,
            "Adversary_ID" : adversary_ids,
            "Adversary_Name" :  adversary_names,
            "Command" : commands,
            "Number_Facts" : num_facts_used,
            "Visibility_Score" : visibility_scores,
            "Executor_Platform" : executor_platforms,
            "Executor_Name" : executor_names,
            "Agent_Protocol" : agent_protocols,
            "Trusted_Status" : agent_trusted_statuses,
            "Agent_Privilege": agent_privileges,
            "Host_Architecture": agent_architectures
        }

        link_success_df = pandas.DataFrame(data_link_success)
        return link_success_df

    # query param1 df according to features in param2 dict
    # used by probability functions to return relevant portions of df
    def query_link_df(self, cur_link_success_df, feature_query_dict):
        # dict of features types, for querying
        dataTypeDict = dict(cur_link_success_df.dtypes)
        # df which will be repeatedly queried
        query_df = cur_link_success_df
        # for each feature and value
        for feat_name, feat_value in feature_query_dict.items():
            if feat_name != "Link_Facts" and dataTypeDict[feat_name]=='object':
                # query by features that are strings
                query_df = query_df.query(feat_name + " == '" + str(feat_value) + "'")
            
            elif feat_name != "Link_Facts" and dataTypeDict[feat_name]=='int64':
                # query by features that are numbers
                query_df = query_df.query(feat_name + " == " + str(feat_value) + "")
            else:
                # query by link_facts (stored in dict)
                for req_fact_type, req_fact_val in feature_query_dict["Link_Facts"].items():
                    # query df for links containing required fact type and required fact value
                    query_df = query_df[query_df['Link_Facts'].apply(lambda x : req_fact_type in x and req_fact_val in x.values())]

        return query_df


    # Basic Success Probability function, returns % of links with features from feature_query_dict that are succesful
    def BaseSuccessProb(self, feature_query_dict):
        link_success_df = self.operations_df
        
        query_df = self.query_link_df(link_success_df, feature_query_dict) # query dataframe for features
        return (100 * query_df['Status'].value_counts(normalize=True)[0]) # return percentage with Status=0

    # NB Link Success Probability
    # Calculates Prob(Status=0 | features in feature_query_dict)
    def NBLinkSuccessProb(self, feature_query_dict):    
        link_success_df = self.operations_df

        num_total_past_links = link_success_df.shape[0]
    
        # P(A)    Probability Status == 0
        status_0_df = self.query_link_df(link_success_df, {"Status" : 0})
        status_0_past_links = status_0_df.shape[0]
        prob_a = status_0_past_links/num_total_past_links 
                                    
        # P(B)    Probability of current features
        current_feature_df = self.query_link_df(link_success_df, feature_query_dict)
        current_feature_links = current_feature_df.shape[0]
        # TODO: INSERT FLAG RELATED EXCEPTION IF TOO FEW DATAPOINTS HERE
        prob_b = current_feature_links/num_total_past_links 
        
        # P(B|A)    Probability of current features in Status == 0 DF
        current_feature_status_0_df = self.query_link_df(status_0_df, feature_query_dict)
        current_feature_status_0_links = current_feature_status_0_df.shape[0]
        prob_b_given_a = current_feature_status_0_links / status_0_past_links
        
        # NB Formula
        # P(A|B) = (P(B|A)*P(A))/P(B)
        return ((prob_b_given_a * prob_a)/prob_b)
        
# Example Call:
# BaseSuccessProb({"Ability_ID": "90c2efaa-8205-480d-8bb6-61d90dbaf81b", "Link_Facts":{'file.sensitive.extension': 'wav'}, "Executor_Platform": "windows"})
# Example Call:
# NBLinkSuccessProb({"Ability_ID": "90c2efaa-8205-480d-8bb6-61d90dbaf81b", "Link_Facts":{'file.sensitive.extension': 'wav'}, "Executor_Platform": "windows"})