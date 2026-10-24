from pathlib import Path
from typing import List, Tuple, Dict, Any

from simulation_engine.gpt_structure import gpt_request_messages
from baking.environment import BakingEnvironment

class Agent:
  def __init__(self, name: str, description: str):
    self.name, self.description = name, description
    self.message_history: List[Dict[str, str]] = []
    self.env = BakingEnvironment(self)

  def perceive(self) -> None:
    progress = self.env.get_progress()
    ingredient_summary = []
    for group_name, ingredients in (
      ("Dry", progress["dry_ingredients"]),
      ("Wet", progress["wet_ingredients"]),
    ):
      amounts = ", ".join(
        f"{item['name']}: {item['current']}/{item['required']}"
        for item in ingredients
      )
      ingredient_summary.append(f"{group_name}: {amounts}")

    completed_steps = [
      step["name"] for step in progress["steps"] if step["status"] == "completed"
    ]
    remaining_steps = [
      step["name"] for step in progress["steps"] if step["status"] != "completed"
    ]
    tools_in_use = [tool for tool, data in self.env.tools.items() if data["used"]]
    oven_temperature = (
      f"{self.env.oven_temperature}°F"
      if self.env.oven_temperature is not None
      else "not preheated"
    )

    env_description = f"""
      Current baking environment:
      Ingredient quantities (current / required):
      {'; '.join(ingredient_summary)}
      Completed steps: {', '.join(completed_steps) or 'none'}
      Remaining steps: {', '.join(remaining_steps) or 'none'}
      Available tools: {', '.join(self.env.tools.keys())}
      Tools already used: {', '.join(tools_in_use) or 'none'}
      Oven temperature: {oven_temperature}"""

    self.message_history.append({
      "role": "user",
      "content": env_description
    })

  def retrieve(self) -> str:
    """Return the recipe sections from the agent's mixed-topic memories."""
    memory_path = (
      Path(__file__).resolve().parent
      / "baking"
      / self.name.lower()
      / "memory"
      / "memory_stream.txt"
    )
    with memory_path.open("r", encoding="utf-8") as memory_file:
      memories = memory_file.read().split("\n\n")

    # The memory file contains unrelated articles as well as two recipe
    # paragraphs. Select those paragraphs by their explicit section headings
    # so the agent receives the recipe without the surrounding noise.
    recipe_sections = []
    for memory in memories:
      section = memory.strip()
      if section.lower().startswith("steps:") or section.lower().startswith("vanilla cake ingredients:"):
        recipe_sections.append(section)

    return "\n\n".join(recipe_sections)

  def act(self) -> str:
    persona = f"""
    You are {self.name}. {self.description} You are baking a cake right now.
    You remember the recipe for the cake:
    {self.retrieve()}

    Follow the recipe in order and use the current environment progress to choose the next incomplete task.
    Do not repeat completed actions or add ingredients that are already at their required amounts.
    Use exact recipe quantities. Take one action at a time.
    Speak in character, without asterisks.
    """

    response = gpt_request_messages(
      messages=[{"role": "system", "content": persona}] + self.message_history)
    return response if isinstance(response, str) else ""


  def reflect(self, response: str) -> None:
    self.message_history.append({"role": "assistant", "content": response})


  def baking_step(self) -> Tuple[str, List[Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    self.perceive()
    action = self.act()
    if not action.strip() or action.strip().startswith("GENERATION ERROR:"):
      message = "The language model request failed, so no baking action was taken."
      self.message_history.append({"role": "user", "content": message})
      return (
        "I'm having trouble reaching the language model, so I couldn't take a baking step.",
        [],
        [],
        [message],
      )

    self.reflect(action)
    attempted, executed, feedbacks = self.env.process_action(action)
    return action, attempted, executed, feedbacks
