from baking.environment import CakeEnvironment, KitchenEnvironment
from baking.pizza_environment import PizzaEnvironment

RECIPES = {
    "cake": CakeEnvironment,
    "pizza": PizzaEnvironment,
}
DEFAULT_RECIPE = "cake"


def get_recipe(name: str) -> type[KitchenEnvironment]:
    """Return the kitchen for a recipe name, falling back to cake."""
    return RECIPES.get(str(name).lower(), RECIPES[DEFAULT_RECIPE])
