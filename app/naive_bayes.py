from . import NB_Model_Class

class LogicalPlanner:

    def __init__(self, operation, planning_svc, stopping_conditions=()):
        self.operation = operation
        self.planning_svc = planning_svc
        self.stopping_conditions = stopping_conditions
        self.stopping_condition_met = False
        self.state_machine = ['bayes_state']
        self.next_bucket = 'bayes_state'   # repeat this bucket until we run out of links.
        # holder for Naive Bayes probability object
        self.NB_probability_obj = None
        print("NB Planner Initialized")

    async def execute(self):
        # if operation data and probabilities not setup
        if self.NB_probability_obj is None:
            print("Begin NB Class Startup Operations")
        #   create Naive Bayes probability object, and pass data_svc object
            self.NB_probability_obj = NB_Model_Class.NBLinkProbabilities(self.planning_svc.get_service('data_svc'))
        #   await necessary API calls + df building
            print("Inititalized Class")
            await self.NB_probability_obj.startup_operations()

            print("Startup Operations Completed")

        # execute main state of planner
        await self.planning_svc.execute_planner(self)

    async def bayes_state(self):

        print("BAYES STATE")

        links_to_use = []

        # Get the first available link for each agent (make sure we maintain the order).
        for agent in self.operation.agents:
            possible_agent_links = await self._get_links(agent=agent)
            print("Possible Agent Links")
            print(possible_agent_links)
            next_link = await self._get_best_link(possible_agent_links)
            if next_link:
                links_to_use.append(await self.operation.apply(next_link))

        if links_to_use:
            # Each agent will run the next available step.
            await self.operation.wait_for_links_completion(links_to_use)
        else:
            # No more links to run.
            print("Finished Operation")
            self.next_bucket = None

    async def _get_links(self, agent=None):
        return await self.planning_svc.get_links(operation=self.operation, agent=agent)

    # helper method to _get_best_link that accepts a link object
    # returns the usable facts from the object in a dict
    # for use by NB Class query
    def useful_facts(self, cur_link):
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


    # Given list of links, returns the link with the highest probability of success
    # that meets user criteria on required data and visibility.
    # If no such link exists then return None
    async def _get_best_link(self, links):
        print("IN GET BEST LINKS")
        print(links)
        # confirm class has necessary data

# NBLinkSuccessProb({"Ability_ID": "90c2efaa-8205-480d-8bb6-61d90dbaf81b", "Link_Facts":{'file.sensitive.extension': 'wav'}, "Executor_Platform": "windows"})

        # link index (in list) to prob success of link 
        link_to_success_dict = dict()
        # query probability of each link and store
        for index in range(len(links)):
            # get link at index
            cur_link = links[index]
            # use data necessary to query NB object to build query dictionary

            # NOTE:
            # with link_feature_query_dict can customize which of 16 features to query by

            # current selection of features:
            link_feature_query_dict = {
                "Ability_ID": str(cur_link.ability.ability_id),
                "Link_Facts": self.useful_facts(cur_link),
                "Executor_Platform": str(cur_link.executor.platform)
            }
            # fetch probability of success
            prob_success = self.NB_probability_obj.NBLinkSuccessProb(link_feature_query_dict)
            print("LINK FEATURES:" , link_feature_query_dict)
            print("LINK PROB SUCCESS:", prob_success)
            # if returned not enough data return, skip current link
            # otherwise save probability
            if prob_success == None:
                print("NO HISTORY OF SUCH LINK")
            else:
                link_to_success_dict[index] = prob_success
        
        # if some of links have sufficient history
        if len(link_to_success_dict.keys()) > 0:
            # TODO: add visiblity related flag conditions here that run based on conditions
            # return best link (with highest prob success)
            print("Best Link", links[max(link_to_success_dict, key=link_to_success_dict.get)])
            return links[max(link_to_success_dict, key=link_to_success_dict.get)]

        # default atomic order implementation for links:
        print("Defaulting to Atomic")
        abil_id_to_link = dict()
        for link in links:
            abil_id_to_link[link.ability.ability_id] = link
        candidate_ids = set(abil_id_to_link.keys())
        for ab_id in self.operation.adversary.atomic_ordering:
            if ab_id in candidate_ids:
                return abil_id_to_link[ab_id]
