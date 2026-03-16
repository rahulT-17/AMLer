# Evalutor / chain evaluator : this will handle the chain policy rules and evaluate them against the data

from .base import BaseEvaluator

class ChainEvaluator(BaseEvaluator) :

    """
    build_graph`: Converts your flat CSV rows into a map of connections.
       Think of it like building a contact list â€” "ACC_A called ACC_B and ACC_C". 
       After this, you can instantly ask "who did ACC_A send to?"

    dfs`: Follows the money trail. Starts at one account, jumps to whoever they sent money to, 
       then jumps again, keeps going until either too many hops or a cycle is found. Like following a thread through a maze.

    Recursive call: This is the engine of DFS. For every neighbor of current account, we call `dfs` again with `hops+1`.
      The function calls itself â€” that's recursion. Each call goes one level deeper until it hits a stop condition.

    evaluate`: The orchestrator. Builds the graph, then tries every account as a starting point, collects all chains found, wraps them in alerts.
    """

    def __init__(self, rule):
        self.rule = rule

    def build_graph(self, transactions) :
        """
        Builds an adjacency list from flat transaction list.
        Result: {"ACC_A": ["ACC_B", "ACC_C"], "ACC_B": ["ACC_D"], ...}
        Each account maps to list of accounts it sent money to.
        """
        graph = {}

        for txn in transactions :
            sender = txn.get("account")          # who sent money
            receiver = txn.get("account.1")          # who received money

            if sender is None or receiver is None :
                continue                           # skip malformed rows

            if sender not in graph :                
                graph[sender] = []                 # first time seeing sender, create empty list

            graph[sender].append(receiver)         # record this connection

            
        return graph
    
    def dfs(self, current, origin, hops, path, graph, found_chains) :
        """
        Depth First Search â€” follows money hop by hop.
        
        current      â€” account we're currently visiting
        origin       â€” account we started from
        hops         â€” how many hops deep we are
        path         â€” list of accounts visited so far
        graph        â€” adjacency list
        found_chains â€” list we append valid chains into
        """
        # gone deeper than rule allows â€” stop this path
        if hops > self.rule.max_hops :
            return    # too deep, stop

        if self.rule.detect_cycles : 
            # CYCLE mode â€” looking for money returning to origin
            if current == origin and hops >= self.rule.min_hops :  # found a cycle back to origin
                found_chains.append(path)
                return 
        else :
            # RANDOM mode â€” any path long enough counts

            if hops >= self.rule.min_hops :  # reached max hops without needing to return to origin
                found_chains.append(path)    # valid chain found
           
        # KEY PART â€” recursive call
        # for every account that current sent money to, follow that trail deeper
        for neighbor in graph.get(current, []):
            if neighbor not in path:          # avoid infinite loops
                self.dfs(
                    neighbor,                 # move to next account
                    origin,                   # origin never changes
                    hops + 1,                 # one hop deeper
                    path + [neighbor],        # extend the path
                    graph,
                    found_chains
                )
        
    async def evaluate(self, transactions) -> list :
        """
        Main entry point.
        Builds graph, runs DFS from every account,
        returns list of alerts for detected chains.
        """

        alerts = []

        # Step 1: build adjacency list from flat transaction list

        graph = self.build_graph(transactions)

        for account in graph:
            found_chains = []

            self.dfs(
                current=account,
                origin=account,
                hops=0,
                path=[account],
                graph=graph,
                found_chains=found_chains,
            )

        # STEP 2 â€” if any chains found, create alerts
        for chain in found_chains:
            alerts.append({
                "rule_id": self.rule.rule_id,
                "rule_name": self.rule.name,
                "chain": chain,           # the full path e.sg. [A, B, C, A]
                "message": f"Chain rule violated: {self.rule.source_text}",
                "severity": self.rule.severity
            })

        return alerts
