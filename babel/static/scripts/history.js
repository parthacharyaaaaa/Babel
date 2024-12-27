async function getHistory(sortOption, filterOption, pageNumber = 1) {
    try {
        const response = await fetch(`/fetch-history?sort=${sortOption}&filter=${filterOption}&page=${pageNumber}`, {
            method: "GET",
            credentials: "include",
            headers: {
                "Content-Type": "application/json",
                "X-CLIENT-TYPE" : "web",
                "X-CSRF-TOKEN" : localStorage.getItem("X-CSRF-TOKEN")
            }
        });

        if (!response.ok) {
            throw new Error(`${response.status}: ${response.statusText}. Failed to fetch history`);
        }
        isExhausted = response.headers.get("exhausted");
        
        results = await response.json();
        const parent = document.querySelector(".history-list");

        results.forEach(result => {
            let entry = document.createElement("li");
            entry.classList.add("history-item");

            let date = document.createElement("span");
            date.innerText = `Time: ${result.time_requested}`;
            date.classList.add("history-date");

            let type = document.createElement("span");
            type.innerText = `Type: ${result.type}`;
            type.classList.add("history-type")

            let language = document.createElement("span");
            if (result.type === "translation"){
                language.innerText = `${result.dst} -> ${result.src}`
            }
            else{
                language.innerText = `Detected Language: ${result.lang}`
            }

            let content = document.createElement("span");
            content.innerText = `Contents: ${result.content}`;
            content.classList.add("history-contents");

            let id = document.createElement("span");
            id.innerText = `ID: ${result.id}`;
            id.classList.add("history-id");

            entry.appendChild(date);
            entry.appendChild(language);
            entry.appendChild(content);
            entry.appendChild(id);

            parent.appendChild(entry);

        })
        if(isExhausted){
            document.getElementById("load-more").remove();
        }
    }
    catch (error) {
        console.error(error);
    }
}
document.addEventListener("DOMContentLoaded", function (event) {
    //Initial Load
    getHistory(0, 0, 1);
    let currentPage = 1;
    const sortBtn = document.getElementById("sort");
    const filterBtn = document.getElementById("filter");

    const selectionBtns = document.querySelectorAll(".selection");
    selectionBtns.forEach(selectionBtn => {
        selectionBtn.addEventListener("input", () => {
            const parent = document.querySelector(".history-list");
            parent.innerHTML = "";
            currentPage = 1;
            getHistory(sortBtn.value, filterBtn.value, currentPage)
        });
        selectionBtn.addEventListener("change", () => {
            const parent = document.querySelector(".history-list");
            parent.innerHTML = "";  
            currentPage = 1;
            getHistory(sortBtn.value, filterBtn.value, currentPage)
        });
    })


    const loadMoreBtn = document.getElementById("load-more");
    loadMoreBtn.addEventListener("click", () => {
        currentPage++;
        getHistory(sortBtn.value, filterBtn.value, currentPage);
    })
})