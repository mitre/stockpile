from app.objects.secondclass.c_fact import Fact
from app.objects.secondclass.c_relationship import Relationship
from app.utility.base_parser import BaseParser


class Parser(BaseParser):
    """
    The static parser allows to create facts after successful ability execution without actually parsing the information from the collected output.
    Instead, the value of the generated fact can be configured directly in the respective ability configuration.

    It was initially designed for usage with planners that link abilities using facts as pre- and post-conditions (e.g. the Look Ahead Planner).
    When using the Look Ahead Planner, abilities are chosen depending on their future reward values that are calculated by linking them via their respective pre- and post-conditions.
    The proposed parser allows the definition of post-conditions that are created in a static manner (i.e. without a specialized parser) to support the linking as executed by the Look Ahead Planner.
    Defining the required fact in a Fact Source would not "motivate" the planner to execute the respective ability.

    Additionally (although not the original use case), when using e.g. the Atomic Planner, the defined fact would only be created if the ability was executed successfully, thus implementing a condition for the execution of an ability that uses the respective fact.

    Example:
        parsers:
          - module: plugins.stockpile.app.parsers.static
            parserconfigs:
              - source fact.value
                custom_parser_vals:
                  source: 'fact value'
              - source: source.fact.value
                edge: has.edge
                target: target.fact.value
                custom_parser_vals:
                  source: 'source fact value'
                  target: 'target fact value'


    Note: Output must be non-empty or parser will not be called at all.
        Optionally, add the following lines in contact_svc.py line 125:

        if ["app.parsers.static" in p.module for p in link.executor.parsers] and not result.output:
            result.output = "c3RhdGljCg==" # static encoded in base64
    """

    def parse(self, blob):
        """
        Create and return relationships with facts and values taken from the respective ability configuration.

        Args:
            blob: Ignored for the actual parsing, but still required because when calling the function we do not differentiate between different parser implementations

        Returns:
            list: A list of relationship object that include the generated facts and values

        """
        relationships = []

        for mp in self.mappers:
            source = mp.custom_parser_vals.get("source", None)
            target = mp.custom_parser_vals.get("target", source)

            if source:
                source = self.set_value(mp.source, source, self.used_facts)
                target = self.set_value(mp.target, target, self.used_facts)
                relationships.append(
                    Relationship(
                        source=Fact(mp.source, source),
                        edge=mp.edge,
                        target=Fact(mp.target, target),
                    )
                )

        return relationships

