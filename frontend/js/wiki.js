document.addEventListener("DOMContentLoaded", () => {
    const searchInput = document.getElementById("searchInput");
    
    searchInput.addEventListener("keypress", function(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            searchRecipe();
        }
    });
});

async function searchRecipe() {
    const query = document.getElementById("searchInput").value.trim();
    if(!query) {
        alert("Введите название предмета");
        return;
    }
    
    const loading = document.getElementById("loading");
    const resultArea = document.getElementById("resultArea");
    const grid = document.getElementById("craftingGrid");
    
    loading.style.display = "block";
    resultArea.style.display = "none";
    
    try {
        const response = await fetch(`/api/wiki/craft?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if(data.status === "success") {
            const recipe = data.recipe;
            
            // Validation
            if(!recipe || !recipe.grid || !Array.isArray(recipe.grid)) {
                alert("Ошибка: некорректный формат рецепта");
                return;
            }
            
            // Validate 3x3 grid
            if(recipe.grid.length !== 3) {
                alert("Ошибка: сетка должна быть 3x3");
                return;
            }
            
            for(let row of recipe.grid) {
                if(!Array.isArray(row) || row.length !== 3) {
                    alert("Ошибка: некорректный формат сетки");
                    return;
                }
            }
            
            // Display recipe
            document.getElementById("recipeName").innerText = recipe.name || query;
            document.getElementById("recipeDesc").innerText = recipe.description || "Описание не доступно";
            
            // Render grid
            grid.innerHTML = "";
            for(let row of recipe.grid) {
                for(let item of row) {
                    const slot = document.createElement("div");
                    slot.className = "crafting-slot";
                    
                    // Check if item is empty
                    const isEmpty = !item || item.toLowerCase().trim() === "пусто" || item === "";
                    
                    if(!isEmpty) {
                        slot.innerText = item;
                        slot.classList.add("slot-filled");
                        slot.title = item;  // Show tooltip on hover
                    }
                    
                    grid.appendChild(slot);
                }
            }
            
            resultArea.style.display = "block";
        } else {
            alert("Ошибка: " + (data.message || "Рецепт не найден"));
        }
    } catch (err) {
        alert("Ошибка сети при обращении к серверу: " + err.message);
        console.error(err);
    } finally {
        loading.style.display = "none";
    }
}
