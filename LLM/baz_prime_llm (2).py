"""
baz_prime_llm.py
=================

This module implements a simplified version of the ELLM (Efficient Language and
Logic Model) that operates entirely in a prime‐encoded domain.  The design is
inspired by the "Prime Encoding in Mathematics" paper and the quantum‐coherent
prime‐domain computation paradigm.  All symbols, numbers and logical
constructs are mapped to products of prime numbers.  Operations in the
encoded domain correspond to arithmetic on the exponent vectors of these
primes, ensuring uniqueness and reversibility of representations【248†L26-L45】.

Key features:
  * **Prime generation and mapping** – An incremental sieve provides primes on
    demand.  Concepts (words) are assigned unique primes; integers are
    factorised into primes for encoding and decoding.
  * **Arithmetic in the encoded domain** – Multiplication and division are
    performed by combining or cancelling exponents (corresponding to the
    operation E(a) ⊗ E(b) = E(a)·E(b)【248†L50-L56】).  Addition and
    subtraction are implemented by decoding to integers, operating in Z and
    reencoding (E(a) ⊕ E(b) = E(a+b), E(a) ⊖ E(b) = E(a-b))【248†L66-L76】.
    Negative numbers are encoded by including a special prime factor for the
    sign【248†L79-L83】.
  * **Concept encoding** – Subjects, predicates and objects of facts are
    assigned primes.  A fact is represented by the product of the primes
    for its subject, predicate and object.  Rules are stored as encoded
    conditions and encoded conclusions.  This mirrors the structure of the
    JavaScript ELLM implementation in the provided ZIP.
  * **Knowledge base and reasoning** – A simple knowledge base stores
    encoded facts and rules.  A reasoning engine can deduce whether a
    query fact is entailed by the knowledge base by checking direct
    containment or by applying universal/capability/standard rules.  It
    employs a depth‐limited search with memoisation to avoid infinite
    recursion.

This module can be used to prototype how the prime‐encoded LLM design
described in the uploaded zip might be ported into a Python context or
integrated with an analogue system like the BAZ EM ladder.  The numeric
operations on the prime encodings could, in principle, be executed by a
prime‐indexed analogue computing substrate such as the BAZ ladder, as
described in the "Pocket‑Sized Majorana Analogues" paper, where a
prime‑frequency comb and programmable phase/gain taps implement
nearest‐neighbour couplings and functional calculus【13†L22-L34】.

Example usage:

>>> kb = KnowledgeBase(encoder)
>>> kb.add_fact(Fact('socrates', 'is', 'human'))
>>> kb.add_rule(Rule.create_universal_rule('human', 'mortal'))
>>> reasoner = ReasoningEngine(encoder)
>>> reasoner.deduce(kb, Fact('socrates', 'is', 'mortal'))
{'result': True, 'explanation': 'Direct fact in knowledge base: socrates is human, and all human are mortal'}

"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

###############################################################################
# Prime generation
###############################################################################

class PrimeGenerator:
    """Generate prime numbers on demand using a simple sieve."""
    def __init__(self, initial_limit: int = 1000) -> None:
        self._primes: List[int] = []
        self._sieve_limit = 0
        self._generate_up_to(initial_limit)

    def _generate_up_to(self, n: int) -> None:
        # Extend the sieve to at least n
        if n <= self._sieve_limit:
            return
        sieve = [True] * (n + 1)
        sieve[0] = sieve[1] = False
        for p in range(2, int(n ** 0.5) + 1):
            if sieve[p]:
                for multiple in range(p * p, n + 1, p):
                    sieve[multiple] = False
        # Merge newly found primes into list
        for i in range(max(2, self._sieve_limit + 1), n + 1):
            if sieve[i]:
                self._primes.append(i)
        self._sieve_limit = n

    def get(self, index: int) -> int:
        """Return the index‐th prime (0‐based)."""
        # Ensure enough primes generated
        current_max = self._primes[-1] if self._primes else 2
        while index >= len(self._primes):
            # Double the sieve range until we have enough primes
            self._generate_up_to(self._sieve_limit * 2 or 1000)
        return self._primes[index]

###############################################################################
# Encoder for integers and concepts
###############################################################################

class PrimeEncoder:
    """
    Assign unique primes to concepts and encode integers via prime factorisation.

    This class maps arbitrary concept strings to distinct prime numbers.  It
    also provides methods to encode and decode integers using unique prime
    factorisation, supporting negative numbers via a dedicated sign prime.

    The encoding operations mirror those defined in the prime encoding paper:
    multiplication (⊗), division (�), addition (⊕), subtraction (⊖) and
    handling of negatives【248†L50-L76】.
    """

    def __init__(self) -> None:
        self.prime_gen = PrimeGenerator(1000)
        self._concept_to_prime: Dict[str, int] = {}
        self._prime_to_concept: Dict[int, str] = {}
        self._next_index: int = 0
        # Reserve a special prime for negative sign encoding
        self.sign_prime = self._assign_prime('_sign')

    def _assign_prime(self, concept: str) -> int:
        p = self.prime_gen.get(self._next_index)
        self._next_index += 1
        self._concept_to_prime[concept] = p
        self._prime_to_concept[p] = concept
        return p

    def get_prime(self, concept: str) -> int:
        """Return the prime representing the given concept, assigning a new one if necessary."""
        key = concept.lower()
        if key in self._concept_to_prime:
            return self._concept_to_prime[key]
        return self._assign_prime(key)

    # Integer encoding/decoding -------------------------------------------------

    def encode_integer(self, n: int) -> Dict[int, int]:
        """Encode an integer as a map from prime to exponent.

        Negative numbers are represented by including the sign prime if the
        integer is negative【248†L79-L83】.  Zero has no prime encoding in this
        framework, so an error is raised.
        """
        if n == 0:
            raise ValueError("Zero cannot be encoded uniquely as a prime product.")
        encoding: Dict[int, int] = {}
        if n < 0:
            encoding[self.sign_prime] = 1
            n = -n
        # Factorise the absolute value
        remaining = n
        # Ensure prime generator has enough primes
        # We'll expand until sqrt(remaining) < last prime
        while True:
            for i in range(self._next_index):
                p = self.prime_gen.get(i)
                if p * p > remaining:
                    break
                while remaining % p == 0:
                    encoding[p] = encoding.get(p, 0) + 1
                    remaining //= p
            break
        if remaining > 1:
            # remaining itself is a prime; ensure prime mapping exists
            # If the remaining prime is not a concept prime, it still needs to
            # be represented in the encoding.  We allow direct integer primes.
            encoding[remaining] = encoding.get(remaining, 0) + 1
        return encoding

    def decode_integer(self, encoding: Dict[int, int]) -> int:
        """Decode a prime‐exponent map back to an integer."""
        sign = 1
        result = 1
        for p, exp in encoding.items():
            if p == self.sign_prime:
                sign *= -1 if exp % 2 == 1 else 1
                continue
            result *= p ** exp
        return sign * result

    def multiply(self, a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
        """E(a) ⊗ E(b) = E(a)·E(b), combine exponents【248†L50-L56】."""
        result: Dict[int, int] = {}
        for p, e in a.items():
            result[p] = result.get(p, 0) + e
        for p, e in b.items():
            result[p] = result.get(p, 0) + e
        # Remove zero exponents if any
        return {p: e for p, e in result.items() if e != 0}

    def divide(self, a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
        """E(a) � E(b) = E(a) / E(b) if divisible【248†L59-L64】."""
        result = a.copy()
        for p, e in b.items():
            if p == self.sign_prime:
                # dividing by negative flips sign if odd exponent
                result[self.sign_prime] = result.get(self.sign_prime, 0) - e
                continue
            have = result.get(p, 0)
            if have < e:
                raise ValueError("Division results in non-integer.")
            result[p] = have - e
            if result[p] == 0:
                del result[p]
        return result

    def add(self, a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
        """E(a) ⊕ E(b) = E(a + b)【248†L66-L73】. Decode, add and reencode."""
        ia = self.decode_integer(a)
        ib = self.decode_integer(b)
        return self.encode_integer(ia + ib)

    def subtract(self, a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
        """E(a) ⊖ E(b) = E(a - b)【248†L73-L76】. Decode, subtract and reencode."""
        ia = self.decode_integer(a)
        ib = self.decode_integer(b)
        return self.encode_integer(ia - ib)

    # Concept encoding/decoding -----------------------------------------------

    def encode_symbol(self, symbol: str) -> Dict[int, int]:
        """Encode a concept/word as a single prime factor with exponent 1."""
        p = self.get_prime(symbol)
        return {p: 1}

    def decode_symbol(self, encoding: Dict[int, int]) -> Optional[str]:
        """Decode a one-factor encoding back to its concept name (if known)."""
        # Only valid for single-prime encodings (excluding sign prime)
        primes = [p for p in encoding if p != self.sign_prime]
        if len(primes) == 1 and encoding[primes[0]] == 1:
            return self._prime_to_concept.get(primes[0])
        return None

###############################################################################
# Facts and rules
###############################################################################

@dataclass
class Fact:
    subject: str
    predicate: str
    object: str

    def __str__(self) -> str:
        return f"{self.subject} {self.predicate} {self.object}"

@dataclass
class Rule:
    conditions: List[Fact]
    conclusion: Fact
    type: str = field(default="standard")  # "standard", "universal", "capability"
    category: Optional[str] = None
    property: Optional[str] = None
    capability: Optional[str] = None

    @staticmethod
    def create_universal_rule(category: str, property: str) -> 'Rule':
        # All X are Y
        var = "_x_"
        return Rule(conditions=[Fact(var, "is", category)],
                    conclusion=Fact(var, "is", property),
                    type="universal",
                    category=category,
                    property=property)

    @staticmethod
    def create_capability_rule(category: str, capability: str) -> 'Rule':
        # All X can Y
        var = "_x_"
        return Rule(conditions=[Fact(var, "is", category)],
                    conclusion=Fact(var, "can", capability),
                    type="capability",
                    category=category,
                    capability=capability)

###############################################################################
# Knowledge base
###############################################################################

class KnowledgeBase:
    """
    Store encoded facts and rules.  Facts are encoded as the product of primes
    representing subject, predicate and object.  Rules store encoded
    conditions and conclusions along with metadata for universals and capabilities.
    """
    def __init__(self, encoder: PrimeEncoder) -> None:
        self.encoder = encoder
        self.fact_encodings: List[Dict[int, int]] = []
        self.rules: List[Dict[str, any]] = []
        self.facts: List[Fact] = []  # Keep original facts for reference

    def add_fact(self, fact: Fact) -> Dict[int, int]:
        enc = self.encode_fact(fact)
        self.fact_encodings.append(enc)
        self.facts.append(fact)
        return enc

    def encode_fact(self, fact: Fact) -> Dict[int, int]:
        s_enc = self.encoder.encode_symbol(fact.subject)
        p_enc = self.encoder.encode_symbol(fact.predicate)
        o_enc = self.encoder.encode_symbol(fact.object)
        # Multiply the three to get a single encoding
        return self.encoder.multiply(self.encoder.multiply(s_enc, p_enc), o_enc)

    def add_rule(self, rule: Rule) -> Dict[str, any]:
        """Encode and store a rule."""
        if rule.type == "universal" or rule.type == "capability":
            cond_enc = self.encode_fact(rule.conditions[0])
            concl_enc = self.encode_fact(rule.conclusion)
            encoded_rule = {
                'type': rule.type,
                'category_prime': self.encoder.get_prime(rule.category),
                'property_prime': self.encoder.get_prime(rule.property) if rule.type == 'universal' else self.encoder.get_prime(rule.capability),
                'predicate_prime': self.encoder.get_prime('is') if rule.type == 'universal' else self.encoder.get_prime('can'),
                'condition_encoding': cond_enc,
                'conclusion_encoding': concl_enc
            }
        else:
            cond_encs = [self.encode_fact(cond) for cond in rule.conditions]
            concl_enc = self.encode_fact(rule.conclusion)
            encoded_rule = {
                'type': 'standard',
                'condition_encodings': cond_encs,
                'conclusion_encoding': concl_enc
            }
        self.rules.append(encoded_rule)
        return encoded_rule

###############################################################################
# Reasoning engine
###############################################################################

class ReasoningEngine:
    """Deduce whether a query fact is entailed by a knowledge base."""
    def __init__(self, encoder: PrimeEncoder) -> None:
        self.encoder = encoder

    def deduce(self, kb: KnowledgeBase, query: Fact) -> Dict[str, any]:
        """Public API for deducing a fact.  Resets the visited set each time."""
        self._visited: Set[str] = set()
        result = self._deduce(kb, query, depth=0)
        return result

    def _deduce(self, kb: KnowledgeBase, query: Fact, depth: int) -> Dict[str, any]:
        key = str(query)
        if key in self._visited:
            return { 'result': False, 'explanation': f"Circular reasoning detected: {query}" }
        self._visited.add(key)

        # Identity membership: any concept is considered to belong to itself.  This
        # allows universal and capability rules to apply to category names (e.g.,
        # 'rings is abelian_groups' can be deduced via the rule 'all rings are
        # abelian_groups' even though no explicit fact 'rings is rings' exists).
        # Without this check the reasoner fails when asked whether a category
        # belongs to its own superset because the requisite membership fact is
        # missing.  Treating X is X as always true resolves that issue.
        if query.predicate == 'is' and query.subject == query.object:
            return { 'result': True, 'explanation': f"{query.subject} is itself by definition" }

        # Transitive closure for universal rules on category hierarchies.  If there
        # is a chain of universal rules A→B→...→Z linking the subject category
        # to the object category, then we can deduce subject is object without
        # requiring explicit membership facts.  This handles cases like
        # 'Hilbert_spaces is normed_spaces', where universal rules are
        # Hilbert_spaces→inner_product_spaces and inner_product_spaces→normed_spaces.
        if query.predicate == 'is':
            # Try to determine if the subject belongs to the object category via universal rules
            try:
                chain = self._universal_chain(kb, query.subject, query.object)
                if chain:
                    # Build a human-readable chain explanation
                    # e.g. ['Hilbert_spaces', 'inner_product_spaces', 'normed_spaces']
                    # yields "Hilbert_spaces are inner_product_spaces, and inner_product_spaces are normed_spaces"
                    parts = []
                    for i in range(len(chain) - 1):
                        parts.append(f"{chain[i]} are {chain[i+1]}")
                    chain_expl = ", and ".join(parts)
                    # Build equation form: subj ⊆ mid1 ⊆ mid2 ... ⊆ target
                    eq_form = " ⊆ ".join(chain)
                    return { 'result': True, 'explanation': chain_expl, 'equation': eq_form }
            except Exception:
                # If an error occurs (e.g., missing encoder), ignore and proceed
                pass

        # Encode the query fact
        q_enc = kb.encode_fact(query)
        # Direct fact present?
        for fact_enc, fact in zip(kb.fact_encodings, kb.facts):
            if fact_enc == q_enc:
                return { 'result': True, 'explanation': f"Direct fact in knowledge base: {fact}" }

        # Check universal/capability rules
        for rule in kb.rules:
            if rule['type'] in ('universal', 'capability'):
                # If predicate matches rule's predicate and object matches property/capability
                if query.predicate == ('is' if rule['type'] == 'universal' else 'can'):
                    # If query.object matches the property's concept name
                    if self.encoder.get_prime(query.object) == rule['property_prime']:
                        # Create membership fact: subject is category
                        membership = Fact(query.subject, 'is', kb.encoder._prime_to_concept[rule['category_prime']])
                        sub_res = self._deduce(kb, membership, depth+1)
                        if sub_res['result']:
                            clause = 'are' if rule['type'] == 'universal' else 'can'
                            # Build equation form for universal or capability rules
                            eq_form = None
                            # If there is an equation from the subresult, extend it; otherwise construct fresh
                            if isinstance(sub_res, dict) and 'equation' in sub_res and sub_res['equation']:
                                # Append the current target
                                eq_form = f"{sub_res['equation']} ⊆ {query.object}"
                            else:
                                # For universal: subject ∈ category ⊆ property
                                if rule['type'] == 'universal':
                                    # Example: subject ∈ category ⊆ property
                                    eq_form = f"{query.subject} ∈ {membership.object} ⊆ {query.object}"
                                else:
                                    # capability: ∀x∈category: x can capability
                                    eq_form = f"∀x∈{membership.object}: x can {query.object}"
                            expl = f"{sub_res['explanation']}, and all {kb.encoder._prime_to_concept[rule['category_prime']]} {clause} {query.object}"
                            return { 'result': True, 'explanation': expl, 'equation': eq_form }

        # Check standard rules
        for rule in kb.rules:
            if rule['type'] == 'standard' and rule['conclusion_encoding'] == q_enc:
                # All conditions must be true
                explanations = []
                all_ok = True
                for cond_enc in rule['condition_encodings']:
                    cond_fact = self._decode_fact(cond_enc, kb)
                    if cond_fact is None:
                        all_ok = False
                        break
                    sub_res = self._deduce(kb, cond_fact, depth+1)
                    if not sub_res['result']:
                        all_ok = False
                        break
                    explanations.append(sub_res['explanation'])
                if all_ok:
                    return { 'result': True, 'explanation': f"{', '.join(explanations)}, which implies {query}" }

        # Try transitive reasoning for 'is' and 'part of'
        if query.predicate in ('is', 'part of'):
            for fact_enc, fact in zip(kb.fact_encodings, kb.facts):
                if fact.subject == query.subject and fact.predicate == query.predicate:
                    intermediate = Fact(fact.object, query.predicate, query.object)
                    sub_res = self._deduce(kb, intermediate, depth+1)
                    if sub_res['result']:
                        return { 'result': True, 'explanation': f"{query.subject} {query.predicate} {fact.object}, and {sub_res['explanation']}" }

        return { 'result': False, 'explanation': f"Could not deduce: {query}" }

    def _is_universal_subset(self, kb: KnowledgeBase, subj: str, target: str, visited: Optional[Set[str]] = None) -> bool:
        """Return True if `subj` is contained in `target` via a chain of universal rules.

        This helper searches the directed graph defined by universal rules
        ("all X are Y"). It returns True if there is a path from `subj`
        to `target` (inclusive), meaning `subj` is a subset of `target`.

        Parameters
        ----------
        kb : KnowledgeBase
            The knowledge base containing universal rules.
        subj : str
            Name of the starting category (subject).
        target : str
            Name of the desired super category (object).
        visited : Optional[Set[str]]
            A set of categories visited in the current DFS to avoid cycles.

        Returns
        -------
        bool
            True if a transitive chain of universal rules connects `subj` to `target`.
        """
        # Direct equality
        if subj == target:
            return True
        # Initialise visited set
        if visited is None:
            visited = set()
        # Avoid cycles
        if subj in visited:
            return False
        visited.add(subj)
        subj_prime = self.encoder.get_prime(subj)
        # Explore universal rules where the category matches subj
        for rule in kb.rules:
            if rule.get('type') != 'universal':
                continue
            # Only consider rules whose category_prime equals subj's prime
            if rule.get('category_prime') != subj_prime:
                continue
            # Determine the property name (super category)
            prop_prime = rule.get('property_prime')
            # Map property prime back to concept name; if not found, skip
            prop_name = self.encoder._prime_to_concept.get(prop_prime)
            if prop_name is None:
                continue
            # If property matches target, success
            if prop_name == target:
                return True
            # Otherwise recurse
            if self._is_universal_subset(kb, prop_name, target, visited):
                return True
        return False

    def _universal_chain(self, kb: KnowledgeBase, subj: str, target: str, visited: Optional[Set[str]] = None) -> Optional[List[str]]:
        """Return a list representing the chain of categories from `subj` to `target` via universal rules.

        If there is a sequence subj → ... → target using universal rules, this returns a list
        [subj, mid1, mid2, ..., target].  If no chain exists, return None.

        Parameters
        ----------
        kb : KnowledgeBase
            The knowledge base with universal rules.
        subj : str
            The starting category.
        target : str
            The target category.
        visited : Optional[Set[str]]
            Set of categories visited to avoid cycles.

        Returns
        -------
        Optional[List[str]]
            The list of categories in the chain, or None if no chain exists.
        """
        # Direct equality yields a trivial chain
        if subj == target:
            return [subj]
        if visited is None:
            visited = set()
        # Avoid cycles
        if subj in visited:
            return None
        visited.add(subj)
        subj_prime = self.encoder.get_prime(subj)
        # Explore outgoing universal rules
        for rule in kb.rules:
            if rule.get('type') != 'universal':
                continue
            if rule.get('category_prime') != subj_prime:
                continue
            prop_prime = rule.get('property_prime')
            prop_name = self.encoder._prime_to_concept.get(prop_prime)
            if not prop_name:
                continue
            # Recurse along the property
            chain = self._universal_chain(kb, prop_name, target, visited)
            if chain:
                return [subj] + chain
        return None

    def _decode_fact(self, enc: Dict[int, int], kb: KnowledgeBase) -> Optional[Fact]:
        # Factorise the encoding into exactly three concept primes (subject, predicate, object)
        # This naive decoder works because each fact encoding is the product of three
        # distinct primes with exponent 1.
        primes: List[int] = []
        for p, e in enc.items():
            if p == self.encoder.sign_prime:
                continue
            for _ in range(e):
                primes.append(p)
        if len(primes) != 3:
            return None
        s, pred, o = primes
        sub = self.encoder._prime_to_concept.get(s)
        prd = self.encoder._prime_to_concept.get(pred)
        obj = self.encoder._prime_to_concept.get(o)
        if sub and prd and obj:
            return Fact(sub, prd, obj)
        return None

###############################################################################
# Demonstration
###############################################################################

def demo() -> None:
    """Demonstrate the prime-encoded LLM on a small knowledge base."""
    enc = PrimeEncoder()
    kb = KnowledgeBase(enc)
    # Add facts
    kb.add_fact(Fact('socrates', 'is', 'human'))
    kb.add_fact(Fact('plato', 'is', 'human'))
    kb.add_fact(Fact('human', 'is', 'mammal'))
    # Add rules
    kb.add_rule(Rule.create_universal_rule('human', 'mortal'))
    kb.add_rule(Rule.create_universal_rule('mammal', 'animal'))
    kb.add_rule(Rule.create_capability_rule('bird', 'fly'))
    # Standard rule: if X is human and X is philosopher then X is wise
    kb.add_fact(Fact('socrates', 'is', 'philosopher'))
    kb.add_rule(Rule(
        conditions=[Fact('_x_', 'is', 'human'), Fact('_x_', 'is', 'philosopher')],
        conclusion=Fact('_x_', 'is', 'wise'),
        type='standard'
    ))
    reasoner = ReasoningEngine(enc)
    # Queries
    queries = [
        Fact('socrates', 'is', 'mortal'),
        Fact('plato', 'is', 'mortal'),
        Fact('human', 'is', 'animal'),
        Fact('socrates', 'is', 'wise'),
        Fact('bird', 'can', 'fly'),
        Fact('penguin', 'can', 'fly')
    ]
    for q in queries:
        res = reasoner.deduce(kb, q)
        print(f"Query: {q}")
        print(f"Result: {'Yes' if res['result'] else 'No'}")
        print(f"Explanation: {res['explanation']}")
        print('-' * 60)

if __name__ == '__main__':
    demo()