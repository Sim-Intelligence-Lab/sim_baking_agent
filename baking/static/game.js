let game;
let gameStates = [];
let currentStep = 0;
let char;
let items = {};
let endScreenImage = null;
let endScreenSnapshot = null;
let scene = null;
let currentRecipe = 'cake';
// Bumped on every recipe start so late replies from an old session are ignored.
let sessionId = 0;

const TILE_SIZE = 16;
const MAP_WIDTH = 8;
const MAP_HEIGHT = 8;
const SCALE = 4;
const WIDTH = MAP_WIDTH * TILE_SIZE * SCALE;
const HEIGHT = MAP_HEIGHT * TILE_SIZE * SCALE;

const WALKABLE_TILES = [0, 98, 101, 100, 99];
const WALKABLE_BEHIND_TILES = [110, 111, 112, 136, 137, 138];
const START_TILE = { x: 4, y: 5 };
// Bump when images change so browsers fetch the new files instead of cached ones.
const ASSET_VERSION = 2;
const asset = path => `static/assets/${path}?v=${ASSET_VERSION}`;

// Per-recipe kitchen setup. `actions` maps each environment action to the
// walk Trang takes for it; `next` continues with the following action.
const RECIPES = {
  cake: {
    subtitle: 'A little flour, a little patience, and one cake coming right up.',
    positions: 'item-positions-cake',
    itemMap: {
      1: 'flour', 2: 'baking_powder', 3: 'salt', 4: 'butter', 5: 'sugar',
      6: 'eggs', 7: 'vanilla_extract', 8: 'milk', 9: 'oven', 10: 'mixing_bowl',
      11: 'large_bowl', 12: 'whisk', 13: 'mixer', 14: 'pans', 15: 'fridge'
    },
    fridgeItems: ['butter', 'milk', 'eggs'],
    endImageFilter: 'LINEAR',
    actions: {
      add_ingredient: (args, next) => {
        const ingredient = args[0];
        const bowl = isWetIngredient(ingredient) ? 'large_bowl' : 'mixing_bowl';
        moveCharTo(ingredient, () => moveCharTo(bowl, next));
      },
      use_tool: (args, next) => moveCharTo(args[0], next),
      preheat_oven: (args, next) => moveCharTo('oven', next),
      mix_ingredients: (args, next) => {
        const type = args[0];
        if (type === 'dry') {
          moveCharTo('mixing_bowl', () => moveCharTo('whisk', next));
        } else if (type === 'wet' || type === 'cream') {
          moveCharTo('large_bowl', () => moveCharTo('mixer', next));
        } else {
          next();
        }
      },
      combine_all_ingredients: (args, next) => moveCharTo('mixing_bowl', () => moveCharTo('large_bowl', next)),
      pour_batter: (args, next) => moveCharTo('large_bowl', () => moveCharTo('pans', next)),
      bake_cake: (args, next) => moveCharTo('pans', () => moveCharTo('oven', next)),
      cool_cake: (args, next) => moveCharTo('oven', () => moveCharTo('pans', next)),
      start_over: (args, next) => moveCharTo('mixing_bowl', () => moveCharTo('large_bowl', next))
    }
  },
  pizza: {
    subtitle: 'Fresh dough, bubbling cheese, and one pizza coming right up.',
    positions: 'item-positions-pizza',
    itemMap: {
      1: 'flour', 2: 'yeast', 3: 'salt', 4: 'water', 5: 'olive_oil',
      6: 'tomato_sauce', 7: 'mozzarella', 8: 'basil', 9: 'oven', 10: 'mixing_bowl',
      11: 'rolling_pin', 12: 'pizza_pan', 13: 'pizza_cutter', 15: 'fridge'
    },
    fridgeItems: ['mozzarella', 'basil'],
    endImageFilter: 'NEAREST',
    actions: {
      add_ingredient: (args, next) => {
        const ingredient = args[0];
        const target = ['tomato_sauce', 'mozzarella', 'basil'].includes(ingredient) ? 'pizza_pan' : 'mixing_bowl';
        moveCharTo(ingredient, () => moveCharTo(target, next));
      },
      use_tool: (args, next) => moveCharTo(args[0], next),
      preheat_oven: (args, next) => moveCharTo('oven', next),
      mix_dough: (args, next) => moveCharTo('mixing_bowl', next),
      knead_dough: (args, next) => moveCharTo('mixing_bowl', next),
      let_dough_rise: (args, next) => moveCharTo('mixing_bowl', next),
      roll_out_dough: (args, next) => moveCharTo('mixing_bowl', () => moveCharTo('rolling_pin', () => moveCharTo('pizza_pan', next))),
      top_pizza: (args, next) => moveCharTo('tomato_sauce', () => moveCharTo('pizza_pan', next)),
      bake_pizza: (args, next) => moveCharTo('pizza_pan', () => moveCharTo('oven', next)),
      slice_pizza: (args, next) => moveCharTo('oven', () => moveCharTo('pizza_cutter', () => moveCharTo('pizza_pan', next))),
      start_over: (args, next) => moveCharTo('mixing_bowl', next)
    }
  }
};

const config = {
  type: Phaser.AUTO,
  width: WIDTH,
  height: HEIGHT,
  parent: 'game-container',
  backgroundColor: '#eef3ef',
  antialias: false,
  pixelArt: true,
  physics: {
    default: 'arcade',
    arcade: { gravity: { y: 0 }, debug: false }
  },
  scene: { preload, create, update }
};

game = new Phaser.Game(config);

let currentTypewriterTimeout;

function typeWriter(text, elementId, speed = 10) {
  const element = document.getElementById(elementId);
  clearTimeout(currentTypewriterTimeout);
  element.innerHTML = '';
  let i = 0;
  function type() {
    if (i < text.length) {
      element.innerHTML += text.charAt(i);
      i++;
      currentTypewriterTimeout = setTimeout(type, speed);
    }
  }
  type();
}

function preload() {
  this.load.image('tiles', asset('kitchen_tileset.png'));
  this.load.tilemapCSV('kitchen-map', asset('kitchen_tilemap.csv'));
  this.load.spritesheet('char', asset('char_spritesheet.png'), { frameWidth: 32, frameHeight: 32 });
  
  const itemImages = new Set();
  Object.values(RECIPES).forEach(recipe => Object.values(recipe.itemMap).forEach(item => {
    if (item !== 'oven' && item !== 'fridge') itemImages.add(item);
  }));
  itemImages.forEach(item => this.load.image(item, asset(`${item}.png`)));
  this.load.tilemapCSV('item-positions-cake', asset('item_positions.csv'));
  this.load.tilemapCSV('item-positions-pizza', asset('pizza_item_positions.csv'));
  Object.keys(RECIPES).forEach(recipe => {
    this.load.image(`success_${recipe}`, asset(`success_${recipe}.png`));
    this.load.image(`bad_${recipe}`, asset(`bad_${recipe}.png`));
  });
}

function create() {
  scene = this;
  const map = this.make.tilemap({ key: 'kitchen-map', tileWidth: TILE_SIZE, tileHeight: TILE_SIZE });
  const tileset = map.addTilesetImage('tiles', 'tiles', TILE_SIZE, TILE_SIZE);
  const layer = map.createLayer(0, tileset, 0, 0).setScale(SCALE);

  [layer.texture, this.textures.get('tiles')].forEach(texture => {
    if (texture) texture.setFilter(Phaser.Textures.NEAREST);
  });
  window.gameLayer = layer.setDepth(100);
  char = this.physics.add.sprite(tileCenter(START_TILE.x), tileCenter(START_TILE.y), 'char', 0)
    .setScale(SCALE / 2);
  if (char.texture) char.texture.setFilter(Phaser.Textures.NEAREST);

  createAnimations.call(this);
  char.play('idle_front');
  updateCharacterDepth();
  createItems(currentRecipe);
  createDebugGrid.call(this);
}

function tileCenter(tile) {
  return tile * TILE_SIZE * SCALE + (TILE_SIZE * SCALE / 2);
}

// Put Trang back at the start and lay out the kitchen for a recipe.
function resetKitchen(recipeKey) {
  if (!scene) return;
  restoreEndScreen();
  scene.tweens.killTweensOf(char);
  char.setPosition(tileCenter(START_TILE.x), tileCenter(START_TILE.y));
  char.play('idle_front');
  updateCharacterDepth();
  createItems(recipeKey);
}

function createAnimations() {
  const animConfig = { frameRate: 10, repeat: -1 };
  ['front', 'left', 'right', 'back'].forEach((direction, index) => {
    this.anims.create({
      key: `idle_${direction}`,
      frames: [{ key: 'char', frame: index * 3 }],
      frameRate: 1,
      repeat: -1
    });
    this.anims.create({
      key: `walk_${direction}`,
      frames: this.anims.generateFrameNumbers('char', { start: index * 3, end: index * 3 + 2 }),
      ...animConfig
    });
  });
}

function createItems(recipeKey) {
  Object.values(items).forEach(item => {
    if (item && item.destroy) item.destroy();
  });
  items = {};

  const recipe = RECIPES[recipeKey];
  const itemPositionsMap = scene.make.tilemap({ key: recipe.positions, tileWidth: TILE_SIZE, tileHeight: TILE_SIZE });
  for (let y = 0; y < MAP_HEIGHT; y++) {
    for (let x = 0; x < MAP_WIDTH; x++) {
      const tile = itemPositionsMap.getTileAt(x, y);
      const itemName = tile && recipe.itemMap[tile.index];
      if (!itemName) continue;

      const itemX = tileCenter(x);
      const itemY = tileCenter(y);
      if (itemName === 'oven' || itemName === 'fridge') {
        items[itemName] = { x: itemX, y: itemY };
        continue;
      }

      items[itemName] = scene.add.image(itemX, itemY, itemName)
        .setScale(SCALE)
        .setVisible(false);
      if (items[itemName].texture) {
        items[itemName].texture.setFilter(Phaser.Textures.NEAREST);
      }
      const mapTile = window.gameLayer.getTileAt(x, y);
      items[itemName].setDepth(mapTile && WALKABLE_BEHIND_TILES.includes(mapTile.index) ? 150 : 200);
    }
  }
}

function createDebugGrid() {
  const graphics = this.add.graphics().lineStyle(2, 0xff0000, 0.0);
  for (let x = 0; x <= MAP_WIDTH; x++) {
    for (let y = 0; y <= MAP_HEIGHT; y++) {
      graphics.strokeRect(x * TILE_SIZE * SCALE, y * TILE_SIZE * SCALE, TILE_SIZE * SCALE, TILE_SIZE * SCALE);
    }
  }
  graphics.setDepth(1000);
}

function update() {}

let isAutoProgressEnabled = false;
let autoProgressTimer = null;
let isStepRequestPending = false;
let isGameCompleted = false;
// Bumped whenever a step is shown so an older walk animation stops early.
let animationToken = 0;

// Play pacing: pause after a new step lands, and between replayed steps.
const AUTO_NEW_STEP_DELAY = 1500;
const AUTO_REPLAY_DELAY = 3000;

function latestStep() {
  return gameStates.length - 1;
}

function requestNextStep() {
  if (isStepRequestPending || isGameCompleted) return;

  const requestSession = sessionId;
  isStepRequestPending = true;
  refreshControls();
  $.post('/next_step')
    .done(function(data) {
      if (requestSession !== sessionId) return;
      isStepRequestPending = false;
      updateGameState(data);
      if (data.completed) {
        stopAutoProgress();
      } else if (isAutoProgressEnabled) {
        scheduleAutoProgress(AUTO_NEW_STEP_DELAY);
      }
    })
    .fail(function() {
      if (requestSession !== sessionId) return;
      isStepRequestPending = false;
      stopAutoProgress();
      typeWriter('The baking step could not be reached. Please try again.', 'speech-box');
    })
    .always(function() {
      if (requestSession !== sessionId) return;
      refreshControls();
    });
}

function scheduleAutoProgress(delay) {
  clearTimeout(autoProgressTimer);
  autoProgressTimer = setTimeout(autoProgress, delay);
}

function autoProgress() {
  if (!isAutoProgressEnabled || isStepRequestPending) return;

  if (currentStep < latestStep()) {
    // Replaying steps already fetched, e.g. after browsing back.
    currentStep++;
    showTimelineState(currentStep);
    refreshControls();
    if (isAutoProgressEnabled) scheduleAutoProgress(AUTO_REPLAY_DELAY);
  } else if (isGameCompleted) {
    stopAutoProgress();
  } else {
    // requestNextStep schedules the next tick when the reply arrives.
    requestNextStep();
  }
}

function startAutoProgress() {
  if (isAutoProgressEnabled || gameStates.length === 0) return;
  if (isGameCompleted && currentStep >= latestStep()) return;
  isAutoProgressEnabled = true;
  refreshControls();
  autoProgress();
}

function stopAutoProgress() {
  isAutoProgressEnabled = false;
  clearTimeout(autoProgressTimer);
  autoProgressTimer = null;
  refreshControls();
}

function updateGameState(data) {
  // Ignore responses already in flight when a completed response arrived.
  if (isGameCompleted) return;
  isGameCompleted = Boolean(data.completed);

  // Follow the new step if the viewer was on the latest one (or playing).
  // If they browsed back, keep their place and just update the counter.
  const wasAtLatest = currentStep >= latestStep();
  gameStates.push(data);
  if (gameStates.length === 1 || wasAtLatest || isAutoProgressEnabled) {
    currentStep = latestStep();
    showTimelineState(currentStep);
  }
  refreshControls();
}

function showTimelineState(index) {
  const state = gameStates[index];
  if (!state) return;

  displayGameState(state);
  if (state.completed) {
    const finalMessage = state.final_message || state.agent_message || "The baking session has ended.";
    endGame(finalMessage, state.result || 'neutral');
  }
}

function displayGameState(state) {
  restoreEndScreen();
  stopWalking();
  typeWriter(state.agent_message || state.message, 'speech-box');
  
  let feedbackHtml = '';
  
  if (state.attempted_actions && state.attempted_actions.length > 0) {
    feedbackHtml += '<h3>Attempted Actions:</h3><ul>';
    state.attempted_actions.forEach(action => {
      feedbackHtml += `<li>${formatAction(action)}${state.executed_actions.some(ea => ea.name === action.name) ? '' : ' (Failed)'}</li>`;
    });
    feedbackHtml += '</ul>';
  }
  
  if (state.feedback) {
    feedbackHtml += '<h3>Environment Feedback:</h3>';
    feedbackHtml += state.feedback.split('\n').map(line => 
      $('<div>').text(line).prop('outerHTML')
    ).join('');
  }
  
  $('#feedback').html(feedbackHtml || 'Nothing yet. Notes show up after each of Trang\'s steps.');
  
  if (state.executed_actions && state.executed_actions.length > 0) {
    processExecutedActions(state.executed_actions);
  }
  
  updateProgress(state.progress);
}

function formatAction(action) {
  const titleCase = value => String(value).replace(/_/g, ' ').replace(/\b\w/g, letter => letter.toUpperCase());
  let formattedAction = titleCase(action.name);
  
  if (action.args && action.args.length > 0) {
    formattedAction += ': ' + action.args.map(value => typeof value === 'string' ? titleCase(value) : value).join(', ');
  }
  
  return formattedAction.charAt(0).toUpperCase() + formattedAction.slice(1);
}

// Stop Trang mid-walk and snap her to the tile she is on.
function stopWalking() {
  animationToken++;
  if (!scene || !char) return;
  scene.tweens.killTweensOf(char);
  char.setPosition(
    tileCenter(Math.floor(char.x / (TILE_SIZE * SCALE))),
    tileCenter(Math.floor(char.y / (TILE_SIZE * SCALE)))
  );
  char.play('idle_front');
  updateCharacterDepth();
}

function processExecutedActions(executedActions) {
  const actionQueue = [...executedActions];
  const actionMap = RECIPES[currentRecipe].actions;
  const token = animationToken;

  function processNextAction() {
    if (token !== animationToken || actionQueue.length === 0) return;
    const action = actionQueue.shift();
    if (actionMap[action.name]) {
      actionMap[action.name](action.args, processNextAction);
    } else {
      console.log(`Unknown action: ${action.name}`);
      processNextAction();
    }
  }

  processNextAction();
}

function isWetIngredient(ingredient) {
  return ['butter', 'sugar', 'eggs', 'vanilla_extract', 'milk'].includes(ingredient.toLowerCase());
}

function findPath(startX, startY, endX, endY) {
  const queue = [[startX, startY]];
  const visited = new Set();
  const parent = new Map();

  while (queue.length > 0) {
    const [x, y] = queue.shift();
    const key = `${x},${y}`;

    if (x === endX && y === endY) {
      return reconstructPath(parent, startX, startY, endX, endY);
    }

    if (!visited.has(key)) {
      visited.add(key);
      [[x + 1, y], [x - 1, y], [x, y + 1], [x, y - 1]].forEach(([nx, ny]) => {
        if (isWalkable(nx, ny) && !visited.has(`${nx},${ny}`)) {
          queue.push([nx, ny]);
          parent.set(`${nx},${ny}`, [x, y]);
        }
      });
    }
  }

  return null;
}

function isWalkable(x, y) {
  if (x < 0 || x >= MAP_WIDTH || y < 0 || y >= MAP_HEIGHT) return false;
  const tile = window.gameLayer.getTileAt(x, y);
  return tile && (WALKABLE_TILES.includes(tile.index) || WALKABLE_BEHIND_TILES.includes(tile.index));
}

function moveCharTo(itemName, callback) {
  let targetX, targetY;

  function moveToTarget(nextCallback) {
    if (targetX !== undefined && targetY !== undefined) {
      const startX = Math.floor(char.x / (TILE_SIZE * SCALE));
      const startY = Math.floor(char.y / (TILE_SIZE * SCALE));
      const targetTile = window.gameLayer.getTileAt(targetX, targetY);
      const isBehindTile = targetTile && WALKABLE_BEHIND_TILES.includes(targetTile.index);

      let path = isBehindTile ? 
        findPath(startX, startY, targetX, targetY) : 
        findAdjacentPath(startX, startY, targetX, targetY);

      if (path) {
        moveAlongPath(path, () => {
          const dx = targetX - Math.floor(char.x / (TILE_SIZE * SCALE));
          const dy = targetY - Math.floor(char.y / (TILE_SIZE * SCALE));
          
          const direction = isBehindTile ? 'front' :
            Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') :
            (dy > 0 ? 'front' : 'back');
          
          char.play(`idle_${direction}`);

          if (itemName !== 'oven' && itemName !== 'fridge' && items[itemName] && !items[itemName].visible) {
            items[itemName].setVisible(true);
          }

          updateCharacterDepth();
          if (nextCallback) nextCallback();
        });
      } else if (nextCallback) nextCallback();
    } else if (nextCallback) nextCallback();
  }

  if (RECIPES[currentRecipe].fridgeItems.includes(itemName)) {
    if (items['fridge']) {
      targetX = Math.floor(items['fridge'].x / (TILE_SIZE * SCALE));
      targetY = Math.floor(items['fridge'].y / (TILE_SIZE * SCALE));
      moveToTarget(() => {
        if (items[itemName]) {
          targetX = Math.floor(items[itemName].x / (TILE_SIZE * SCALE));
          targetY = Math.floor(items[itemName].y / (TILE_SIZE * SCALE));
          moveToTarget(callback);
        } else if (callback) callback();
      });
    } else if (callback) callback();
  } else {
    const item = items[itemName];
    if (item) {
      targetX = Math.floor(item.x / (TILE_SIZE * SCALE));
      targetY = Math.floor(item.y / (TILE_SIZE * SCALE));
      moveToTarget(callback);
    } else if (callback) callback();
  }
}

function findAdjacentPath(startX, startY, targetX, targetY) {
  for (const [adjX, adjY] of [[targetX - 1, targetY], [targetX + 1, targetY], [targetX, targetY - 1], [targetX, targetY + 1]]) {
    if (isWalkable(adjX, adjY)) {
      const tempPath = findPath(startX, startY, adjX, adjY);
      if (tempPath) return tempPath;
    }
  }
  return null;
}

function reconstructPath(parent, startX, startY, endX, endY) {
  const path = [];
  let current = [endX, endY];
  while (current[0] !== startX || current[1] !== startY) {
    path.unshift(current);
    current = parent.get(`${current[0]},${current[1]}`);
  }
  return path;
}

function moveAlongPath(path, callback) {
  if (path.length === 0) {
    updateCharacterDepth();
    if (callback) callback();
    return;
  }

  const [nextX, nextY] = path.shift();
  const targetX = nextX * TILE_SIZE * SCALE + (TILE_SIZE * SCALE / 2);
  const targetY = nextY * TILE_SIZE * SCALE + (TILE_SIZE * SCALE / 2);

  const dx = targetX - char.x;
  const dy = targetY - char.y;

  const direction = Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'front' : 'back');

  char.play(`walk_${direction}`);

  game.scene.scenes[0].tweens.add({
    targets: char,
    x: targetX,
    y: targetY,
    duration: 200,
    ease: 'Linear',
    onComplete: () => {
      updateCharacterDepth();
      moveAlongPath(path, callback);
    }
  });
}

function updateCharacterDepth() {
  const tileX = Math.floor(char.x / (TILE_SIZE * SCALE));
  const tileY = Math.floor(char.y / (TILE_SIZE * SCALE));
  const tile = window.gameLayer.getTileAt(tileX, tileY);
  
  if (tile) {
    char.setDepth(WALKABLE_BEHIND_TILES.includes(tile.index) ? 90 : 150);
  }
}

function updateNavigationButtons() {
  const hasStates = gameStates.length > 0;
  const atLatest = currentStep >= latestStep();
  // Browsing steps already fetched works even while Trang is thinking.
  $('#prev-step').prop('disabled', !hasStates || currentStep <= 0);
  $('#next-step').prop(
    'disabled',
    !hasStates || (atLatest && (isStepRequestPending || isGameCompleted))
  );
  $('.recipe-option').prop('disabled', isStepRequestPending);

  const canPlay = hasStates && !(isGameCompleted && atLatest);
  $('#auto-progress')
    .text(isAutoProgressEnabled ? 'Pause Simulation' : 'Play Simulation')
    .toggleClass('active', isAutoProgressEnabled)
    .attr('aria-pressed', String(isAutoProgressEnabled))
    .prop('disabled', !isAutoProgressEnabled && !canPlay);
}

function refreshControls() {
  updateNavigationButtons();
  updateCurrentStepDisplay();
}

function updateProgress(progress) {
  $('#steps').empty();
  progress.steps.forEach(function(step) {
    var li = $('<li>').text(step.name);
    if (step.status === 'completed') {
      li.addClass('completed');
    }
    if (step.tools) {
      var toolList = $('<ul>');
      step.tools.forEach(function(tool) {
        var toolLi = $('<li>').text(tool.name);
        if (tool.used) {
          toolLi.addClass('tool-used');
        }
        toolList.append(toolLi);
      });
      li.append(toolList);
    }
    $('#steps').append(li);
  });

  const groups = $('#ingredient-groups').empty();
  (progress.ingredient_groups || []).forEach(function(group) {
    const section = $('<section class="ingredient-section">');
    section.append($('<h3>').text(group.title));
    const list = $('<ul class="ingredient-list">');
    group.items.forEach(function(ing) {
      const fill = ing.required ? Math.min(ing.current / ing.required, 1) * 100 : 0;
      list.append($('<li>')
        .css('--fill', `${fill}%`)
        .toggleClass('done', ing.current === ing.required)
        .toggleClass('over', ing.current > ing.required)
        .append(
          $('<span>').text(ing.name),
          $('<span>').text(`${ing.current}/${ing.required}`)
        ));
    });
    groups.append(section.append(list));
  });
}

function testCharacterMovement() {
  const ingredients = ['flour', 'baking_powder', 'salt', 'butter', 'sugar', 'eggs', 'vanilla_extract', 'milk'];
  let currentIndex = 0;

  function moveToNextIngredient() {
    if (currentIndex < ingredients.length) {
      const ingredient = ingredients[currentIndex];
      moveCharTo(ingredient, () => {
        setTimeout(() => {
          currentIndex++;
          moveToNextIngredient();
        }, 1000);
      });
    }
  }

  moveToNextIngredient();
}

function testToolMovement() {
  const tools = ['mixing_bowl', 'large_bowl', 'whisk', 'mixer', 'pans', 'oven'];
  let currentIndex = 0;

  function moveToNextTool() {
    if (currentIndex < tools.length) {
      const tool = tools[currentIndex];
      moveCharTo(tool, () => {
        setTimeout(() => {
          currentIndex++;
          moveToNextTool();
        }, 1000);
      });
    }
  }

  moveToNextTool();
}

function endGame(message, status = 'neutral') {
  stopAutoProgress();
  updateNavigationButtons();
  
  const imageName = status === 'success' ? `success_${currentRecipe}` :
                    status === 'bad' ? `bad_${currentRecipe}` : null;
  
  if (imageName) {
    displayEndImage(imageName);
  }
  
  typeWriter(message, 'speech-box');
}

function displayEndImage(imageName) {
  endScreenSnapshot = scene.children.list.map(child => [child, child.visible]);
  endScreenSnapshot.forEach(([child]) => {
    child.setVisible(false);
  });
  scene.cameras.main.setBackgroundColor('#FFFFFF');

  endScreenImage = scene.add.image(WIDTH / 2, HEIGHT / 2, imageName);
  endScreenImage.setScale(Math.min(WIDTH / endScreenImage.width, HEIGHT / endScreenImage.height));
  endScreenImage.setDepth(1000);
  endScreenImage.setVisible(true);

  if (endScreenImage.texture) {
    endScreenImage.texture.setFilter(Phaser.Textures[RECIPES[currentRecipe].endImageFilter]);
  }
}

function restoreEndScreen() {
  if (endScreenImage) {
    endScreenImage.destroy();
    endScreenImage = null;
  }
  if (!endScreenSnapshot) return;

  endScreenSnapshot.forEach(([child, wasVisible]) => {
    if (child.active) child.setVisible(wasVisible);
  });
  endScreenSnapshot = null;
  scene.cameras.main.setBackgroundColor('#eef3ef');
}

function updateCurrentStepDisplay() {
  if (gameStates.length === 0) {
    $('#current-step').text('Preparing the kitchen…');
    return;
  }
  let text = `Step ${currentStep} of ${Math.max(0, latestStep())}`;
  if (isStepRequestPending) {
    text += ' · Trang is thinking…';
  } else if (currentStep < latestStep()) {
    text += ' · viewing an earlier step';
  } else if (isGameCompleted) {
    text += ' · finished';
  }
  $('#current-step').text(text);
}

// Manual Next/Previous take over from Play.
function goToNextStep() {
  stopAutoProgress();
  if (currentStep < latestStep()) {
    currentStep++;
    showTimelineState(currentStep);
  } else if (!isStepRequestPending && !isGameCompleted) {
    requestNextStep();
  }
  refreshControls();
}

function goToPreviousStep() {
  stopAutoProgress();
  if (currentStep <= 0) return;
  currentStep--;
  showTimelineState(currentStep);
  refreshControls();
}

function startRecipe(recipeKey) {
  if (!RECIPES[recipeKey] || isStepRequestPending) return;

  stopAutoProgress();
  sessionId++;
  const requestSession = sessionId;
  currentRecipe = recipeKey;
  gameStates = [];
  currentStep = 0;
  isGameCompleted = false;

  $('.recipe-option').each(function() {
    $(this).attr('aria-pressed', String($(this).data('recipe') === recipeKey));
  });
  $('.app-subtitle').text(RECIPES[recipeKey].subtitle);
  $('#feedback').text("Trang's feedback will appear here.");
  typeWriter('Getting the kitchen ready…', 'speech-box');
  resetKitchen(recipeKey);

  isStepRequestPending = true;
  refreshControls();
  $.ajax({
    url: '/start_baking',
    method: 'POST',
    contentType: 'application/json',
    data: JSON.stringify({ recipe: recipeKey })
  })
    .done(function(data) {
      if (requestSession !== sessionId) return;
      isStepRequestPending = false;
      updateGameState(data);
    })
    .fail(function() {
      if (requestSession !== sessionId) return;
      isStepRequestPending = false;
      typeWriter('The kitchen could not be reached. Please refresh the page.', 'speech-box');
    })
    .always(function() {
      if (requestSession !== sessionId) return;
      refreshControls();
    });
}

$(document).ready(function() {

  startRecipe(currentRecipe);

  $('.recipe-option').click(function() {
    const recipeKey = $(this).data('recipe');
    if (recipeKey !== currentRecipe) startRecipe(recipeKey);
  });

  $('#next-step').click(goToNextStep);
  $('#prev-step').click(goToPreviousStep);

  $('#test-movement').click(function() {
    testCharacterMovement();
  });

  $('#test-tool-movement').click(function() {
    testToolMovement();
  });

  $('#auto-progress').click(function() {
    if (isAutoProgressEnabled) {
      stopAutoProgress();
    } else {
      startAutoProgress();
    }
  });

});
