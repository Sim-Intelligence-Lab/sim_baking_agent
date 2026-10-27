import json
import os
from flask import Flask, jsonify, render_template, request

from baking_agent import Agent
from baking.recipes import DEFAULT_RECIPE, RECIPES

def init_agent() -> Agent:
    agent_path = os.path.join("baking", "trang", "agent.json")
    with open(agent_path, "r", encoding="utf-8") as f:
        agent_json = json.load(f)

    return Agent(agent_json["name"], agent_json["description"])

app = Flask(
    __name__,
    static_folder="baking/static",
    template_folder="baking/templates",
)

agent = init_agent()
current_step = 0
# The recipe has 22 numbered instructions; allow retries while keeping a cap.
max_steps = 60

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_baking', methods=['POST'])
def start_baking():
    global current_step
    current_step = 0
    recipe = str((request.get_json(silent=True) or {}).get("recipe", DEFAULT_RECIPE))
    agent.set_recipe(recipe if recipe in RECIPES else DEFAULT_RECIPE)
    initial_message = f"Hi there! I'm {agent.name}, and I absolutely love baking. I'm so excited to bake a {agent.recipe} today!"
    agent.message_history = [{"role": "assistant", "content": initial_message}]
    
    return jsonify({
        "recipe": agent.recipe,
        "message": initial_message,
        "progress": agent.env.get_progress(),
        "completed": False,
        "feedback": "",
        "executed_actions": []
    })

@app.route('/next_step', methods=['POST'])
def next_step():
    global current_step
    if current_step < max_steps and not agent.env._all_steps_completed():
        current_step += 1
        
        agent_message, attempted_actions, executed_actions, feedbacks = agent.baking_step()
        
        feedback = '\n'.join(feedbacks)
        progress = agent.env.get_progress()
        
        if agent.env._all_steps_completed():
            dish = agent.recipe
            succeeded = agent.env.check_final_ingredients()
            final_message = f"Wonderful! We've successfully baked the {dish}. Let's enjoy it!" if succeeded else f"Hmm... it seems we made some mistakes with the ingredients and the {dish} tastes... not so good. Let's try again next time!"
            agent.message_history.append({"role": "assistant", "content": final_message})
            return jsonify({
                "recipe": dish,
                "result": "success" if succeeded else "bad",
                "agent_message": agent_message,
                "final_message": final_message,
                "progress": progress,
                "completed": True,
                "feedback": feedback,
                "attempted_actions": attempted_actions,
                "executed_actions": executed_actions
            })
        
        return jsonify({
            "recipe": agent.recipe,
            "agent_message": agent_message,
            "progress": progress,
            "completed": False,
            "feedback": feedback,
            "attempted_actions": attempted_actions,
            "executed_actions": executed_actions
        })
    else:
        timeout_message = f"Oh dear, it seems we've taken too long to bake the {agent.recipe}. Let's try again another time!"
        return jsonify({
            "recipe": agent.recipe,
            "result": "timeout",
            "agent_message": timeout_message,
            "final_message": timeout_message,
            "progress": agent.env.get_progress(),
            "completed": True,
            "feedback": "",
            "attempted_actions": [],
            "executed_actions": []
        })

if __name__ == '__main__':
    app.run(debug=True)
