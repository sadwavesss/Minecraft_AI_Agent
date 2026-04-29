// Recipes database (loaded from JSON)
let recipes = [];
let favorites = new Set();
let currentRecipe = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadRecipes();
    setupEventListeners();
    switchPage('home');
    loadFavorites();
});

// Setup event listeners
function setupEventListeners() {
    // Navigation
    document.querySelectorAll('[data-page]').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const page = link.getAttribute('data-page');
            switchPage(page);
        });
    });

    // Category filters
    document.querySelectorAll('.category-link').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const category = link.getAttribute('data-category');
            switchPage('library');
            filterRecipes(category);
        });
    });

    // Recipe filters
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const filter = btn.getAttribute('data-filter');
            filterRecipes(filter);
        });
    });

    // Search
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchRecipes(e.target.value);
        });
    }

    // Sort
    const sortSelect = document.getElementById('sort-select');
    if (sortSelect) {
        sortSelect.addEventListener('change', (e) => {
            sortRecipes(e.target.value);
        });
    }

    // View toggle
    const viewToggle = document.getElementById('view-toggle');
    if (viewToggle) {
        viewToggle.addEventListener('change', () => {
            // Toggle between grid and list view
            const grid = document.getElementById('recipes-grid');
            grid.classList.toggle('list-view');
        });
    }

    // Modal close
    const modal = document.getElementById('recipe-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                closeRecipeModal();
            }
        });
    }

    // Wiki search
    const wikiSearch = document.getElementById('wiki-search');
    if (wikiSearch) {
        wikiSearch.addEventListener('input', (e) => {
            searchWiki(e.target.value);
        });
    }
}

// Load recipes from JSON
async function loadRecipes() {
    try {
        const response = await fetch('/api/recipes');
        const data = await response.json();
        
        if (data.recipes) {
            recipes = Object.entries(data.recipes).map(([key, recipe]) => ({
                id: key,
                ...recipe,
                emoji: getRecipeEmoji(key),
                category: categorizeRecipe(key)
            }));
        } else {
            // Fallback: load comprehensive recipes
            recipes = [
                {
                    id: 'палка',
                    name: 'Палка',
                    description: 'Основной материал для инструментов и оружия',
                    emoji: '📏',
                    category: 'materials'
                },
                {
                    id: 'деревянная кирка',
                    name: 'Деревянная кирка',
                    description: 'Начальный инструмент для добычи камня',
                    emoji: '🔨',
                    category: 'tools'
                }
            ];
        }
        
        displayRecipes(recipes);
    } catch (error) {
        console.error('Error loading recipes:', error);
        displayRecipeError('Failed to load recipes');
    }
}

// Categorize recipe
function categorizeRecipe(key) {
    const lowerKey = key.toLowerCase();
    
    if (lowerKey.includes('кирка') || lowerKey.includes('топор') || lowerKey.includes('лопата') || lowerKey.includes('мотыга') || lowerKey.includes('верстак') || lowerKey.includes('печь')) {
        return 'tools';
    }
    if (lowerKey.includes('меч') || lowerKey.includes('лук') || lowerKey.includes('стрела')) {
        return 'weapons';
    }
    if (lowerKey.includes('шлем') || lowerKey.includes('нагрудник') || lowerKey.includes('штаны') || lowerKey.includes('сапоги') || lowerKey.includes('броня')) {
        return 'armor';
    }
    if (lowerKey.includes('блок') || lowerKey.includes('кирпич') || lowerKey.includes('песок') || lowerKey.includes('булыжник') || lowerKey.includes('плита') || lowerKey.includes('стекло') || lowerKey.includes('сундук') || lowerKey.includes('дверь')) {
        return 'blocks';
    }
    if (lowerKey.includes('факел') || lowerKey.includes('светильник') || lowerKey.includes('коралл') || lowerKey.includes('столб') || lowerKey.includes('кровля') || lowerKey.includes('забор') || lowerKey.includes('люк') || lowerKey.includes('карпет') || lowerKey.includes('кровать')) {
        return 'decoration';
    }
    if (lowerKey.includes('редстоун') || lowerKey.includes('поршень') || lowerKey.includes('диспенсер') || lowerKey.includes('воронка') || lowerKey.includes('повторитель') || lowerKey.includes('компаратор')) {
        return 'redstone';
    }
    
    return 'other';
}

// Get recipe emoji
function getRecipeEmoji(key) {
    const lowerKey = key.toLowerCase();
    
    if (lowerKey.includes('кирка')) return '⛏️';
    if (lowerKey.includes('топор')) return '🪓';
    if (lowerKey.includes('лопата')) return '🪜';
    if (lowerKey.includes('меч')) return '⚔️';
    if (lowerKey.includes('лук')) return '🏹';
    if (lowerKey.includes('шлем')) return '🪖';
    if (lowerKey.includes('нагрудник')) return '🛡️';
    if (lowerKey.includes('штаны')) return '👖';
    if (lowerKey.includes('сапоги')) return '👢';
    if (lowerKey.includes('броня')) return '🛡️';
    if (lowerKey.includes('кровать')) return '🛏️';
    if (lowerKey.includes('сундук')) return '🧳';
    if (lowerKey.includes('дверь')) return '🚪';
    if (lowerKey.includes('факел')) return '🔦';
    if (lowerKey.includes('светильник')) return '💡';
    if (lowerKey.includes('блок')) return '🧱';
    if (lowerKey.includes('печь')) return '🔥';
    if (lowerKey.includes('верстак')) return '🏗️';
    if (lowerKey.includes('редстоун')) return '⚡';
    if (lowerKey.includes('поршень')) return '⏹️';
    if (lowerKey.includes('коралл')) return '🪸';
    if (lowerKey.includes('забор')) return '🚧';
    if (lowerKey.includes('люк')) return '📦';
    if (lowerKey.includes('перила')) return '🪜';
    if (lowerKey.includes('столб')) return '📏';
    
    return '🔨';
}

// Display recipes
function displayRecipes(recipesToShow) {
    const grid = document.getElementById('recipes-grid');
    if (!grid) return;
    
    grid.innerHTML = '';
    
    if (recipesToShow.length === 0) {
        grid.innerHTML = '<p style="grid-column: 1/-1; color: #8892a1; text-align: center;">No recipes found</p>';
        return;
    }
    
    recipesToShow.forEach(recipe => {
        const card = document.createElement('div');
        card.className = 'recipe-card';
        if (favorites.has(recipe.id)) {
            card.classList.add('favorited');
        }
        
        card.innerHTML = `
            <div class="recipe-card-image">${recipe.emoji || '🔨'}</div>
            <div class="recipe-card-content">
                <div class="recipe-card-name">${recipe.name}</div>
                <div class="recipe-card-description">${recipe.description || 'No description'}</div>
            </div>
        `;
        
        card.addEventListener('click', () => showRecipeModal(recipe));
        grid.appendChild(card);
    });
}

// Show recipe modal
function showRecipeModal(recipe) {
    currentRecipe = recipe;
    const modal = document.getElementById('recipe-modal');
    
    document.getElementById('modal-recipe-name').textContent = recipe.name;
    document.getElementById('modal-recipe-description').textContent = recipe.description || 'No description available';
    
    // Display crafting grid
    const gridContainer = document.getElementById('modal-recipe-grid');
    gridContainer.innerHTML = '';
    
    if (recipe.grid && Array.isArray(recipe.grid)) {
        recipe.grid.forEach(row => {
            if (Array.isArray(row)) {
                row.forEach(item => {
                    const cell = document.createElement('div');
                    cell.className = 'recipe-grid-cell';
                    cell.textContent = item && item !== 'пусто' ? item : '';
                    gridContainer.appendChild(cell);
                });
            }
        });
    } else {
        gridContainer.innerHTML = '<p>Grid data not available</p>';
    }
    
    // Update favorite button
    const favBtn = document.getElementById('favorite-btn');
    if (favorites.has(recipe.id)) {
        favBtn.textContent = '⭐ Remove from Favorites';
        favBtn.classList.add('favorited');
    } else {
        favBtn.textContent = '⭐ Add to Favorites';
        favBtn.classList.remove('favorited');
    }
    
    modal.classList.add('active');
}

// Close recipe modal
function closeRecipeModal() {
    document.getElementById('recipe-modal').classList.remove('active');
}

// Toggle favorite
function toggleFavorite() {
    if (!currentRecipe) return;
    
    if (favorites.has(currentRecipe.id)) {
        favorites.delete(currentRecipe.id);
    } else {
        favorites.add(currentRecipe.id);
    }
    
    saveFavorites();
    updateRecipeCards();
    
    // Update button
    const favBtn = document.getElementById('favorite-btn');
    if (favorites.has(currentRecipe.id)) {
        favBtn.textContent = '⭐ Remove from Favorites';
        favBtn.classList.add('favorited');
    } else {
        favBtn.textContent = '⭐ Add to Favorites';
        favBtn.classList.remove('favorited');
    }
}

// Filter recipes
function filterRecipes(filter) {
    let filtered = recipes;
    
    if (filter === 'favorites') {
        filtered = recipes.filter(r => favorites.has(r.id));
    } else if (filter === 'all') {
        filtered = recipes;
    } else {
        filtered = recipes.filter(r => r.category === filter);
    }
    
    displayRecipes(filtered);
}

// Search recipes
function searchRecipes(query) {
    if (!query.trim()) {
        displayRecipes(recipes);
        return;
    }
    
    const lowerQuery = query.toLowerCase();
    const filtered = recipes.filter(r => 
        r.name.toLowerCase().includes(lowerQuery) ||
        r.description.toLowerCase().includes(lowerQuery) ||
        r.id.toLowerCase().includes(lowerQuery)
    );
    
    displayRecipes(filtered);
}

// Sort recipes
function sortRecipes(sortBy) {
    let sorted = [...recipes];
    
    switch(sortBy) {
        case 'name':
            sorted.sort((a, b) => a.name.localeCompare(b.name));
            break;
        case 'popular':
            sorted.sort((a, b) => favorites.has(b.id) - favorites.has(a.id));
            break;
        case 'recent':
            // Would need timestamp data
            break;
    }
    
    displayRecipes(sorted);
}

// Search wiki
function searchWiki(query) {
    const resultsContainer = document.getElementById('wiki-results');
    if (!resultsContainer) return;
    
    if (!query.trim()) {
        resultsContainer.innerHTML = '';
        return;
    }
    
    const lowerQuery = query.toLowerCase();
    const results = recipes.filter(r => 
        r.name.toLowerCase().includes(lowerQuery) ||
        r.description.toLowerCase().includes(lowerQuery)
    );
    
    resultsContainer.innerHTML = results.map(r => `
        <div style="background: #1b2838; border: 1px solid #2a3f5f; border-radius: 8px; padding: 16px; cursor: pointer;" onclick="showRecipeModal(recipes.find(x => x.id === '${r.id}'))">
            <h3 style="color: #1e90ff; margin: 0 0 8px 0;">${r.emoji || '🔨'} ${r.name}</h3>
            <p style="color: #c7d5e0; margin: 0;">${r.description}</p>
        </div>
    `).join('');
}

// Save favorites to localStorage
function saveFavorites() {
    localStorage.setItem('minecraft_favorites', JSON.stringify(Array.from(favorites)));
}

// Load favorites from localStorage
function loadFavorites() {
    const saved = localStorage.getItem('minecraft_favorites');
    if (saved) {
        favorites = new Set(JSON.parse(saved));
    }
}

// Update recipe cards (for favorite status)
function updateRecipeCards() {
    document.querySelectorAll('.recipe-card').forEach(card => {
        const name = card.querySelector('.recipe-card-name').textContent;
        const recipe = recipes.find(r => r.name === name);
        
        if (recipe && favorites.has(recipe.id)) {
            card.classList.add('favorited');
        } else {
            card.classList.remove('favorited');
        }
    });
}

// Switch pages
function switchPage(pageName) {
    // Hide all pages
    document.querySelectorAll('.page-content').forEach(page => {
        page.classList.remove('active');
    });
    
    // Show selected page
    const pageId = `${pageName}-page`;
    const page = document.getElementById(pageId);
    if (page) {
        page.classList.add('active');
        
        // Load data for specific pages
        if (pageName === 'library') {
            displayRecipes(recipes);
        } else if (pageName === 'favorites') {
            const favoriteRecipes = recipes.filter(r => favorites.has(r.id));
            const favGrid = document.getElementById('favorites-grid');
            if (favGrid) {
                displayRecipes(favoriteRecipes);
            }
        }
    }
    
    // Update navigation
    document.querySelectorAll('.nav-item').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-page') === pageName) {
            link.classList.add('active');
        }
    });
}

// Display recipe error
function displayRecipeError(message) {
    const grid = document.getElementById('recipes-grid');
    if (grid) {
        grid.innerHTML = `<p style="color: #c41e3a;">${message}</p>`;
    }
}

// Utility: Format recipe grid display
function formatRecipeGrid(grid) {
    if (!grid || !Array.isArray(grid)) return '';
    
    return grid.map(row => 
        Array.isArray(row) ? row.join(' | ') : ''
    ).join('\n');
}
