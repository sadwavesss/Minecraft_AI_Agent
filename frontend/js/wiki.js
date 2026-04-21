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
    if(!query) return;
    
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
            document.getElementById("recipeName").innerText = recipe.name || query;
            document.getElementById("recipeDesc").innerText = recipe.description || "Описания нет.";
            
            // Render grid
            grid.innerHTML = "";
            for(let row of recipe.grid) {
                for(let item of row) {
                    const slot = document.createElement("div");
                    slot.className = "crafting-slot";
                    if(item && item !== "пусто") {
                        slot.innerText = item;
                        slot.classList.add("slot-filled");
                    }
                    grid.appendChild(slot);
                }
            }
            
            resultArea.style.display = "block";
        } else {
            alert("Ошибка: " + data.message);
        }
    } catch (err) {
        alert("Ошибка сети при обращении к серверу.");
        console.error(err);
    } finally {
        loading.style.display = "none";
    }
}
