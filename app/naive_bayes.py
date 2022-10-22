from . import NB_Model_Class

from typing import List, Dict


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
        visibility setting in advanced section of operation creation. Calculated as = 99.0-self.operation.visibility. Default is 48%

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
        # holder for Naive Bayes probability object
        self.NB_probability_obj = None
        # min number of datapoints per link for NB calculations, from parameter in planner .yml
        self.min_link_data = min_link_data
        # minimum probability of success needed for link to run, set by user visibility parameter
        self.min_probability_link_success = (99.0-self.operation.visibility)/(100)  # 0-1.0
        print("Minimum REQUIRED PROB OF SUCCESS TO RUN LINK:", self.min_probability_link_success)
        print("NB Planner Initialized")
        self.links_executed = 0

    async def execute(self):
        print("naive_bayes.execute()")

        #   create Naive Bayes probability object, and pass data_svc object
        self.NB_probability_obj = NB_Model_Class.NBLinkProbabilities(self.planning_svc.get_service('data_svc'))

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
            await self.NB_probability_obj.startup_operations()

        links_to_use = []

        # Get the first available link for each agent (make sure we maintain the order).
        for agent in self.operation.agents:
            possible_agent_links = await self._get_links(agent=agent)
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

    async def _get_links(self, agent: Agent = None):
        return await self.planning_svc.get_links(operation=self.operation, agent=agent)

    # Given list of links, returns the link with the highest probability of success
    # that meets user criteria on required data and visibility (AKA risk).
    # If no such link exists then default to atomic ordering planner logic for unknown links
    async def _get_best_link(self, links : List[Link]):
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
                "Link_Facts": self.NB_probability_obj.useful_link_facts(cur_link),
                "Executor_Platform": str(cur_link.executor.platform)
            }
            # fetch probability of success of link with set of features
            print("For link:\n" , link_feature_query_dict)
            prob_success = self.NB_probability_obj.NBLinkSuccessProb(link_feature_query_dict, self.min_link_data)
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
