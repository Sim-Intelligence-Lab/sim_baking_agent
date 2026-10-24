import re
from typing import List, Optional, Tuple

from baking.environment import KitchenEnvironment


class PizzaEnvironment(KitchenEnvironment):
    DISH = "pizza"
    MEMORY_HEADINGS = ("pizza ingredients:", "pizza steps:")
    OVEN_TEMPERATURE = 475
    INGREDIENTS = {
        "flour": 500, "yeast": 7, "salt": 10, "water": 325, "olive_oil": 30,
        "tomato_sauce": 200, "mozzarella": 250, "basil": 8,
    }
    DOUGH = ["flour", "yeast", "salt", "water", "olive_oil"]
    TOPPINGS = ["tomato_sauce", "mozzarella", "basil"]
    INGREDIENT_GROUPS = [("Dough", DOUGH), ("Toppings", TOPPINGS)]
    INGREDIENT_ALIASES = {
        "olive_oil": ("olive oil", "oil"),
        "tomato_sauce": ("tomato sauce", "pizza sauce", "sauce"),
        "mozzarella": ("mozzarella", "cheese"),
        "basil": ("basil", "basil leaves"),
    }
    TOOLS = ["oven", "mixing_bowl", "rolling_pin", "pizza_pan", "pizza_cutter"]
    STEPS = ["preheat_oven", "prepare_pan", "mix_dough", "knead_dough", "let_dough_rise", "roll_out_dough", "top_pizza", "bake_pizza", "slice_pizza"]
    STEP_TOOLS = {
        "mix_dough": [("mixing_bowl", "Mixing Bowl")],
        "roll_out_dough": [("rolling_pin", "Rolling Pin"), ("pizza_pan", "Pizza Pan")],
        "slice_pizza": [("pizza_cutter", "Pizza Cutter")],
    }
    PAN_TOOL = "pizza_pan"
    PAN_STEP = "prepare_pan"
    PAN_MESSAGE = "You oiled the pizza pan and set it out."
    ACTION_HINT = "mix dough, knead dough, let dough rise, roll out dough, top pizza, bake pizza, slice pizza"

    TOOL_PATTERN = re.compile(r"(mixing[_ ]bowl|rolling[_ ]pin|pizza[_ ]pan|pizza[_ ]cutter|cutter|pan|oven)")
    TOOL_NAMES = {"cutter": "pizza_cutter", "pan": "pizza_pan"}

    def _action_prompt_rules(self) -> str:
        return """- For dough: "mix dough", "knead dough", "let dough rise", "roll out dough"
        - For toppings: "top pizza" (spread the sauce and arrange the toppings once they are added)
        - For oven actions: "preheat oven to X degrees", "bake pizza"
        - For other actions: "slice pizza"

        Example:
        Input: "I'll grab the mixing bowl and add 500 grams of flour"
        Your response: "use mixing_bowl, add 500 flour"

        Input: "Time to take out the rolling pin and roll the dough into a nice round"
        Your response: "use rolling_pin, roll out dough\""""

    def _detect_actions(self, text: str) -> Optional[List[Tuple[callable, Tuple]]]:
        if self._is_start_over(text):
            return [(self.start_over, ())]
        actions = []
        # A phrase like "use the rolling pin to roll out dough" names a tool
        # and an action, so pick up the tool first and keep looking.
        if re.search(r"\b(get|use|grab|take)\b", text):
            match = self.TOOL_PATTERN.search(text)
            if match:
                tool = match.group(1).replace(' ', '_')
                actions.append((self.use_tool, (self.TOOL_NAMES.get(tool, tool),)))

        if 'preheat' in text:
            match = re.search(r'(\d+)', text)
            if not match:
                return None
            actions.append((self.preheat_oven, (int(match.group(1)),)))
        elif 'bake' in text:
            actions.append((self.bake_pizza, ()))
        elif 'slice' in text or 'cut pizza' in text:
            actions.append((self.slice_pizza, ()))
        elif 'knead' in text:
            actions.append((self.knead_dough, ()))
        elif 'rise' in text or 'proof' in text:
            actions.append((self.let_dough_rise, ()))
        elif re.search(r"\broll(ed)? (out )?(the )?dough\b", text):
            actions.append((self.roll_out_dough, ()))
        elif any(word in text for word in ('top pizza', 'topping', 'spread', 'assemble')):
            actions.append((self.top_pizza, ()))
        elif re.search(r"\bmix(ed)? (the )?dough\b", text):
            actions.append((self.mix_dough, ()))
        elif re.search(r"\badd\b", text):
            return actions + self._detect_ingredient_add(text)
        return actions or None

    def _sort_actions(self, actions: List[Tuple[callable, Tuple]]) -> List[Tuple[callable, Tuple]]:
        # Within one turn: empty the bowls first, then set up (tools,
        # ingredients, oven) so a step like "top pizza" sees the toppings
        # added in the same sentence.
        setup = {"use_tool", "add_ingredient", "preheat_oven"}

        def order(action):
            name = action[0].__name__
            return 0 if name == "start_over" else 1 if name in setup else 2

        return sorted(actions, key=order)

    def _missing(self, names: List[str]) -> List[str]:
        return [name for name in names if self.ingredients[name]["current"] == 0]

    def mix_dough(self) -> None:
        missing = self._missing(self.DOUGH)
        if not self.tools["mixing_bowl"]["used"]:
            self._send_feedback("You need to get the mixing bowl before mixing the dough")
        elif missing:
            self._send_feedback(f"You are missing the following dough ingredients: {', '.join(missing)}")
        else:
            self.steps_completed.add("mix_dough")
            self._send_feedback("You stirred the flour, yeast, salt, water, and olive oil into a shaggy dough")
            self._shortfall_note(self.DOUGH)

    def knead_dough(self) -> None:
        if "mix_dough" in self.steps_completed:
            self.steps_completed.add("knead_dough")
            self._send_feedback("You kneaded the dough for 8-10 minutes until it was smooth and stretchy")
        else:
            self._send_feedback("Please mix the dough before kneading it")

    def let_dough_rise(self) -> None:
        if "knead_dough" in self.steps_completed:
            self.steps_completed.add("let_dough_rise")
            self._send_feedback("You covered the bowl and let the dough rise for 1 hour until doubled in size")
        else:
            self._send_feedback("Please knead the dough before letting it rise")

    def roll_out_dough(self) -> None:
        if "let_dough_rise" not in self.steps_completed:
            self._send_feedback("Please let the dough rise before rolling it out")
        elif not self.tools["rolling_pin"]["used"]:
            self._send_feedback("You need to take out the rolling pin to roll out the dough")
        elif not self.tools["pizza_pan"]["prepared"]:
            self._send_feedback("Please prepare the pizza pan before rolling out the dough")
        else:
            self.steps_completed.add("roll_out_dough")
            self._send_feedback("You rolled the dough into a 12-inch round and placed it on the pizza pan")

    def top_pizza(self) -> None:
        missing = self._missing(self.TOPPINGS)
        if "roll_out_dough" not in self.steps_completed:
            self._send_feedback("Please roll out the dough before adding toppings")
        elif missing:
            self._send_feedback(f"You still need to add these toppings: {', '.join(missing)}")
        else:
            self.steps_completed.add("top_pizza")
            self._send_feedback("You spread the tomato sauce and arranged the mozzarella and basil evenly")
            self._shortfall_note(self.TOPPINGS)

    def bake_pizza(self) -> None:
        if "top_pizza" not in self.steps_completed:
            self._send_feedback("Please top the pizza before baking it")
        elif not self.tools["oven"]["preheated"]:
            self._send_feedback(f"Please preheat the oven to {self.OVEN_TEMPERATURE}°F first")
        elif self.oven_temperature != self.OVEN_TEMPERATURE:
            self._send_feedback(f"The oven temperature should be {self.OVEN_TEMPERATURE}°F, but it's currently set to {self.oven_temperature}°F")
        else:
            self.steps_completed.add("bake_pizza")
            self._send_feedback("You baked the pizza for 12-15 minutes until the crust was golden and the cheese bubbled")

    def slice_pizza(self) -> None:
        if "bake_pizza" not in self.steps_completed:
            self._send_feedback("Please bake the pizza first")
        elif not self.tools["pizza_cutter"]["used"]:
            self._send_feedback("You need to take out the pizza cutter to slice the pizza")
        else:
            self.steps_completed.add("slice_pizza")
            self._send_feedback("You sliced the pizza into 8 pieces")
