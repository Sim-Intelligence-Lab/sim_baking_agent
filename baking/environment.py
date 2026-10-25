import re
from typing import List, Tuple, Dict, Any, Optional

from simulation_engine.gpt_structure import gpt_request


class ActionRefused(Exception):
    """An action the kitchen turned down; the message is sent as feedback."""


class KitchenEnvironment:
    """Shared kitchen rules. Each recipe subclass fills in the class settings
    below and adds its own actions."""

    DISH = ""
    # Section headings in the agent's memory file that hold this recipe.
    MEMORY_HEADINGS: Tuple[str, ...] = ()
    INGREDIENTS: Dict[str, int] = {}
    # (title shown in the UI, ingredient names) in display order.
    INGREDIENT_GROUPS: List[Tuple[str, List[str]]] = []
    INGREDIENT_ALIASES: Dict[str, Tuple[str, ...]] = {}
    TOOLS: List[str] = []
    STEPS: List[str] = []
    # Steps that list the tools they need in the progress panel.
    STEP_TOOLS: Dict[str, List[Tuple[str, str]]] = {}
    PAN_TOOL = ""
    PAN_STEP = ""
    PAN_MESSAGE = ""
    # Recipe step actions, listed back to the agent when a phrase matches nothing.
    ACTION_HINT = ""

    def __init__(self, agent):
        self.agent = agent
        self.feedbacks = []
        self.reset()

    def reset(self) -> None:
        self.state = "initial"
        self.ingredients = {
            name: {"required": required, "current": 0}
            for name, required in self.INGREDIENTS.items()
        }
        self.tools = {tool: {"used": False} for tool in self.TOOLS}
        self.tools["oven"]["preheated"] = False
        self.tools[self.PAN_TOOL]["prepared"] = False
        self.steps_completed = set()
        self.oven_temperature = None
        self._reset_mixing_state()

    def _reset_mixing_state(self) -> None:
        """Hook for recipe-specific flags that start over with the bowls."""

    def _send_feedback(self, message: str) -> None:
        self.feedbacks.append(message)
        self.agent.message_history.append({"role": "user", "content": message})

    # -- Action parsing -----------------------------------------------------

    def _action_prompt_rules(self) -> str:
        """Recipe-specific lines for the action extraction prompt."""
        raise NotImplementedError

    def _detect_actions(self, processed_action: str) -> Optional[List[Tuple[callable, Tuple]]]:
        """Map one simple lowercase action to environment calls. Return None
        when the phrase matches no kitchen action."""
        raise NotImplementedError

    def _after_detect(self, detected_actions: List[Tuple[callable, Tuple]]) -> None:
        """Hook for recipes that infer extra actions from a whole turn."""

    def _sort_actions(self, actions: List[Tuple[callable, Tuple]]) -> List[Tuple[callable, Tuple]]:
        return actions

    def process_action(self, action: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
        self.feedbacks = []
        processed_actions = self.extract_action(action)
        if (
            not isinstance(processed_actions, str)
            or not processed_actions.strip()
            or processed_actions.strip().startswith("GENERATION ERROR:")
        ):
            self._send_feedback(
                "I couldn't interpret that action because the language model request failed. Please try again."
            )
            return [], [], self.feedbacks

        detected_actions = []
        for processed_action in processed_actions.split(','):
            text = processed_action.strip().strip('"\'.').lower()
            if not text:
                continue
            found = self._detect_actions(text)
            if found is None:
                # Say so instead of silently skipping, so the agent can rephrase
                # rather than repeating the same plan forever.
                self._send_feedback(
                    f"Nothing happened for \"{text}\". Kitchen actions are: add [amount] [ingredient], "
                    f"use [tool], start over, preheat oven to [degrees], {self.ACTION_HINT}."
                )
            else:
                detected_actions.extend(found)
        self._after_detect(detected_actions)

        sorted_actions = self._sort_actions(detected_actions)
        attempted_actions = []
        executed_actions = []

        for action_func, args in sorted_actions:
            attempted_action = {"name": action_func.__name__, "args": args}
            attempted_actions.append(attempted_action)
            try:
                action_func(*args)
                executed_actions.append(attempted_action)
            except ActionRefused as e:
                self._send_feedback(str(e))
            except Exception as e:
                self._send_feedback(f"Failed to execute {action_func.__name__}: {str(e)}")

        if self._all_steps_completed():
            self.check_final_ingredients()

        return attempted_actions, executed_actions, self.feedbacks

    START_OVER_WORDS = ("start over", "start fresh", "clear the bowl", "clear mixing", "throw out", "discard")

    def _is_start_over(self, processed_action: str) -> bool:
        return any(word in processed_action for word in self.START_OVER_WORDS)

    def _detect_ingredient_add(self, processed_action: str) -> List[Tuple[callable, Tuple]]:
        ingredient_add = self._parse_ingredient_add(processed_action)
        if ingredient_add:
            return [(self.add_ingredient, ingredient_add)]
        self._send_feedback(
            f"I couldn't identify a valid ingredient and quantity in: {processed_action}"
        )
        return []

    def _parse_ingredient_add(self, action: str) -> Optional[Tuple[str, int]]:
        """Find a recipe ingredient and quantity even when units are included."""
        normalized_action = action.lower().replace('_', ' ')
        amount_match = re.search(r"(\d+)", normalized_action)
        if not amount_match:
            return None

        candidates = []
        for ingredient in self.ingredients:
            names = self.INGREDIENT_ALIASES.get(ingredient, (ingredient.replace('_', ' '),))
            candidates.extend((name, ingredient) for name in names)

        for name, ingredient in sorted(candidates, key=lambda candidate: len(candidate[0]), reverse=True):
            if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", normalized_action):
                return ingredient, int(amount_match.group(1))

        return None

    def extract_action(self, action: str) -> str:
        prompt = f"""
        Given a description of a baker's action, extract the action and arguments.
        Provide a comma-separated list of simple actions. ONLY the following actions are allowed:
        - For adding ingredients: "add [quantity in number only, no units] [ingredient name]"
        Valid ingredients are: {', '.join(ingredient.replace(' ', '_') for ingredient in self.ingredients.keys())}
        - For getting or using tools: "get / use [tool name]"
        Valid tools are: {', '.join(tool.replace(' ', '_') for tool in self.tools.keys() if tool != 'oven')}
        - To throw out everything in the bowls and begin again: "start over"
        {self._action_prompt_rules()}

        Rules:
        - Only list actions the baker is doing in this message. Skip actions they say are already done or that they will do later.
        - Pair each quantity with the ingredient named right next to it. "add the 325ml of warm water" is "add 325 water".

        Input: {action}
        """
        response = gpt_request(prompt, model="gpt-4o", max_tokens=100)
        return response

    # -- Progress -----------------------------------------------------------

    def get_progress(self) -> Dict[str, Any]:
        progress = {"steps": [], "ingredient_groups": []}

        for step in self.STEPS:
            status = "completed" if step in self.steps_completed else "incomplete"
            entry = {"name": step.replace('_', ' ').title(), "status": status}
            if step in self.STEP_TOOLS:
                entry["tools"] = [
                    {"name": name, "used": self.tools[tool]["used"]}
                    for tool, name in self.STEP_TOOLS[step]
                ]
            progress["steps"].append(entry)

        for title, names in self.INGREDIENT_GROUPS:
            progress["ingredient_groups"].append({
                "title": title,
                "items": [
                    {
                        "name": name.replace('_', ' ').title(),
                        "current": self.ingredients[name]["current"],
                        "required": self.ingredients[name]["required"],
                    }
                    for name in names
                ],
            })

        return progress

    def _all_steps_completed(self) -> bool:
        return self.steps_completed == set(self.STEPS)

    def check_final_ingredients(self) -> bool:
        errors = [f"{i}: expected {d['required']}, got {d['current']}" for i, d in self.ingredients.items() if d["current"] != d["required"]]
        if errors:
            self._send_feedback(f"Your {self.DISH} didn't turn out quite right... Here are the issues with the ingredients:")
            for e in errors:
                self._send_feedback(e)
            return False
        else:
            self._send_feedback(f"You successfully baked a delicious {self.DISH}!")
            return True

    # -- Shared actions -----------------------------------------------------

    def add_ingredient(self, ingredient: str, amount: int) -> None:
        if ingredient in self.ingredients:
            data = self.ingredients[ingredient]
            # The agent often recaps what it already added; don't count that twice.
            if data["current"] >= data["required"]:
                raise ActionRefused(
                    f"Skipped adding {amount} {ingredient}: it already has {data['current']} "
                    f"and the recipe needs {data['required']}. Move on to the next step."
                )
            data["current"] += amount
            message = f"Added {amount} {ingredient}"
            if data["current"] > data["required"]:
                message += (
                    f". That makes {data['current']} {ingredient}, but the recipe needs {data['required']}. "
                    "That's too much. To fix it, start over to empty the bowls, then add the exact amounts again."
                )
            self._send_feedback(message)
        else:
            self._send_feedback(f"You tried to add {amount} {ingredient}, but {ingredient} is not a valid ingredient")

    def use_tool(self, tool: str) -> None:
        if tool in self.tools:
            self.tools[tool]["used"] = True
            if tool == self.PAN_TOOL:
                self.tools[tool]["prepared"] = True
                self.steps_completed.add(self.PAN_STEP)
                self._send_feedback(self.PAN_MESSAGE)
            elif tool == "oven":
                if self.oven_temperature is not None:
                    self.tools[tool]["preheated"] = True
                    self.steps_completed.add("preheat_oven")
                    self._send_feedback(f"You used the oven, which is preheated to {self.oven_temperature}°F")
                else:
                    self._send_feedback("You tried to use the oven, but it's not preheated yet.")
            else:
                self._send_feedback(f"Using {tool}")
        else:
            self._send_feedback(f"You tried to use {tool}, but {tool} is not a valid tool")

    def _shortfall_note(self, names) -> None:
        """Point out ingredients still below their recipe amount after a mix."""
        short = [
            f"{name} is at {self.ingredients[name]['current']} but the recipe needs {self.ingredients[name]['required']}"
            for name in names
            if self.ingredients[name]["current"] < self.ingredients[name]["required"]
        ]
        if short:
            self._send_feedback("Heads up: " + "; ".join(short) + ". Add the rest before moving on.")

    def start_over(self) -> None:
        """Empty the bowls: ingredients and mixing steps reset, but the
        preheated oven and prepared pan stay ready."""
        # Only a real overfill needs a reset. Phrases like "empty the dough onto
        # the counter" must not wipe out good progress.
        if not any(d["current"] > d["required"] for d in self.ingredients.values()):
            raise ActionRefused(
                "No need to start over: no ingredient is over its recipe amount. "
                "Keep going with the next step."
            )
        for data in self.ingredients.values():
            data["current"] = 0
        self.steps_completed &= {"preheat_oven", self.PAN_STEP}
        self._reset_mixing_state()
        self._send_feedback(
            "You threw out the mixture and washed the bowls. Every ingredient is back to 0, "
            "so add each one again with the exact recipe amount."
        )

    def preheat_oven(self, temperature: int) -> None:
        self.oven_temperature = temperature
        self.tools["oven"]["preheated"] = True
        self.steps_completed.add("preheat_oven")
        self._send_feedback(f"You preheated the oven to {self.oven_temperature}°F")


class CakeEnvironment(KitchenEnvironment):
    DISH = "cake"
    MEMORY_HEADINGS = ("steps:", "vanilla cake ingredients:")
    INGREDIENTS = {
        "flour": 250, "baking_powder": 2, "salt": 1, "butter": 230,
        "sugar": 300, "eggs": 4, "vanilla_extract": 2, "milk": 240,
    }
    INGREDIENT_GROUPS = [
        ("Dry Ingredients", ["flour", "baking_powder", "salt"]),
        ("Wet Ingredients", ["butter", "sugar", "eggs", "vanilla_extract", "milk"]),
    ]
    INGREDIENT_ALIASES = {"eggs": ("egg", "eggs")}
    TOOLS = ["oven", "mixing_bowl", "large_bowl", "whisk", "mixer", "pans"]
    STEPS = ["preheat_oven", "prepare_pans", "mix_dry_ingredients", "cream", "mix_wet_ingredients", "combine_all_ingredients", "pour_batter", "bake_cake", "cool_cake"]
    STEP_TOOLS = {
        "mix_dry_ingredients": [("mixing_bowl", "Mixing Bowl"), ("whisk", "Whisk")],
        "cream": [("large_bowl", "Large Bowl"), ("mixer", "Mixer")],
        "mix_wet_ingredients": [("large_bowl", "Large Bowl"), ("mixer", "Mixer")],
    }
    PAN_TOOL = "pans"
    PAN_STEP = "prepare_pans"
    PAN_MESSAGE = "You prepared the cake pans."
    ACTION_HINT = "mix dry ingredients, cream butter and sugar, mix wet ingredients, combine all ingredients, pour batter, bake cake, cool cake"

    def _reset_mixing_state(self) -> None:
        self.dry_mixed = self.wet_mixed = self.cream_done = False

    def _action_prompt_rules(self) -> str:
        return """- For mixing: "mix dry ingredients", "mix wet ingredients", "cream butter and sugar", "combine all ingredients"
        - For oven actions: "preheat oven to X degrees", "bake cake"
        - For other actions: "pour batter", "cool cake"

        Example:
        Input: "I'm going to grab the whisk and mix the dry ingredients"
        Your response: "use whisk, mix dry ingredients"

        Input: "Now I'll add 4 eggs, one at a time, then mix it all together with the mixer"
        Your response: "add 4 eggs, use mixer, mix wet ingredients"

        Input: "I'll gently fold the dry ingredients into the wet batter, then pour it into the pans"
        Your response: "combine all ingredients, pour batter\""""

    TOOL_PATTERN = re.compile(r"(mixing[_ ]bowl|large[_ ]bowl|whisk|mixer|pans|oven)")

    def _detect_actions(self, text: str) -> Optional[List[Tuple[callable, Tuple]]]:
        if self._is_start_over(text):
            return [(self.start_over, ())]

        actions = []
        # "use the mixer to mix wet ingredients" names a tool and a step.
        if re.search(r"\b(get|use|grab|take)\b", text):
            match = self.TOOL_PATTERN.search(text)
            if match:
                actions.append((self.use_tool, (match.group(1).replace(' ', '_'),)))

        mixing = re.search(r"\b(mix|mixed|whisk|stir|blend|beat)\b", text)
        if 'preheat' in text:
            match = re.search(r'(\d+)', text)
            if not match:
                return None
            actions.append((self.preheat_oven, (int(match.group(1)),)))
        elif 'bake' in text:
            actions.append((self.bake_cake, ()))
        elif 'pour' in text:
            actions.append((self.pour_batter, ()))
        elif 'cool' in text:
            actions.append((self.cool_cake, ()))
        elif 'cream' in text:
            actions.append((self.mix_ingredients, ("cream",)))
        elif 'combine' in text or 'fold' in text or ('dry' in text and 'wet' in text):
            actions.append((self.combine_all_ingredients, ()))
        elif 'dry' in text and mixing:
            actions.append((self.mix_ingredients, ("dry",)))
        elif 'wet' in text and mixing:
            actions.append((self.mix_ingredients, ("wet",)))
        elif re.search(r"\badd\b", text):
            return actions + self._detect_ingredient_add(text)

        return actions or None

    def _after_detect(self, detected_actions: List[Tuple[callable, Tuple]]) -> None:
        if any(func.__name__ == 'mix_ingredients' and args[0] == 'dry' for func, args in detected_actions) and \
           any(func.__name__ == 'mix_ingredients' and args[0] == 'wet' for func, args in detected_actions):
            detected_actions.append((self.combine_all_ingredients, ()))

    def _sort_actions(self, actions: List[Tuple[callable, Tuple]]) -> List[Tuple[callable, Tuple]]:
        dependencies = {
            self.mix_ingredients: [self.use_tool],
            self.combine_all_ingredients: [lambda: self.mix_ingredients("dry"), lambda: self.mix_ingredients("wet")],
            self.pour_batter: [self.combine_all_ingredients],
            self.bake_cake: [self.pour_batter, self.preheat_oven]
        }

        def dependencies_satisfied(action, completed_actions):
            return action not in dependencies or all(any(isinstance(dep, type(ca)) for ca in completed_actions) for dep in dependencies[action])

        sorted_actions = []
        completed_actions = set()

        while actions:
            for action in actions:
                if dependencies_satisfied(action[0], completed_actions):
                    sorted_actions.append(action)
                    completed_actions.add(action[0])
                    actions.remove(action)
                    break
            else:
                sorted_actions.extend(actions)
                break

        return sorted_actions

    def mix_ingredients(self, type: str) -> None:
        if type == "cream":
            required_tools = ["large_bowl", "mixer"]
            ingredients = ["butter", "sugar"]
        elif type == "dry":
            required_tools = ["mixing_bowl", "whisk"]
            ingredients = ["flour", "baking_powder", "salt"]
        else:  # wet
            required_tools = ["large_bowl", "mixer"]
            ingredients = ["eggs", "vanilla_extract", "milk"]

        if all(self.ingredients[ing]["current"] > 0 for ing in ingredients):
            if all(self.tools[tool]["used"] for tool in required_tools):
                if type == "cream":
                    self.cream_done = True
                    self.steps_completed.add("cream")
                    self._send_feedback("You creamed the butter and sugar until light and fluffy")
                else:
                    setattr(self, f"{type}_mixed", True)
                    self.steps_completed.add(f"mix_{type}_ingredients")
                    self._send_feedback(f"You mixed the {type} ingredients in the {'mixing' if type == 'dry' else 'large'} bowl with the {'whisk' if type == 'dry' else 'mixer'}")
                self._shortfall_note(ingredients)
            else:
                missing_tools = [tool for tool in required_tools if not self.tools[tool]['used']]
                self._send_feedback(f"You need to use {', '.join(required_tools)} to {'cream the butter and sugar, and are missing' if type == 'cream' else f'mix the {type} ingredients, and are missing'}: {', '.join(missing_tools)}")
        else:
            missing = [ing for ing in ingredients if self.ingredients[ing]["current"] == 0]
            self._send_feedback(f"You are missing the following ingredients for {'creaming' if type == 'cream' else f'{type} mixture'}: {', '.join(missing)}")

    def combine_all_ingredients(self) -> None:
        if self.dry_mixed and self.wet_mixed:
            self.steps_completed.add("combine_all_ingredients")
            self._send_feedback("You combined all the ingredients together")
        else:
            if not self.dry_mixed:
                self._send_feedback("You need to mix the dry ingredients before combining all ingredients")
            if not self.wet_mixed:
                self._send_feedback("You need to mix the wet ingredients before combining all ingredients")

    def pour_batter(self) -> None:
        if "combine_all_ingredients" in self.steps_completed and self.tools["pans"]["prepared"]:
            self.steps_completed.add("pour_batter")
            self._send_feedback("You poured the batter evenly into the prepared cake pans")
        else:
            self._send_feedback("You need to combine all ingredients and prepare cake pans first")

    def bake_cake(self) -> None:
        if "pour_batter" in self.steps_completed and self.tools["oven"]["preheated"]:
            if self.oven_temperature == 350:
                self.steps_completed.add("bake_cake")
                self._send_feedback("You baked the cake for 30-35 minutes")
            else:
                self._send_feedback(f"The oven temperature should be 350°F, but it's currently set to {self.oven_temperature}°F")
        elif "pour_batter" not in self.steps_completed:
            self._send_feedback("Please pour the batter into the pans first")
        elif not self.tools["oven"]["preheated"]:
            self._send_feedback("Please preheat the oven to 350°F first")
        else:
            self._send_feedback("Please pour the batter and preheat the oven to 350°F first")

    def cool_cake(self) -> None:
        if "bake_cake" in self.steps_completed:
            self.steps_completed.add("cool_cake")
            self._send_feedback("You let the pans sit for 10 minutes, then cooled the cake on a wire rack")
        else:
            self._send_feedback("Please bake the cake first")


# Kept so existing imports of BakingEnvironment still get the cake kitchen.
BakingEnvironment = CakeEnvironment
