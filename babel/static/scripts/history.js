async function getHistory(sortOption, filterOption, pageNumber = 1) {
    try {
        const response = await fetch(`/fetch-history?sort=${sortOption}&filter=${filterOption}&page=${pageNumber}`, {
            method: "GET",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            }
        });

        if (!response.ok) {
            throw new Error(`${response.status}: ${response.statusText}. Failed to fetch history`);
        }
        results = await response.json();
        const parent = document.querySelector(".history-list");

        results.forEach(result => {
            let entry = document.createElement("li");
            entry.classList.add("history-item");

            let date = document.createElement("span");
            date.innerText = `Time: ${result.time_requested}`;
            date.classList.add("history-date");

            let content = document.createElement("span");
            content.innerText = `Contents: ${result.content}`;
            content.classList.add("history-contents");

            let id = document.createElement("span");
            id.innerText = `ID: ${result.id}`;
            id.classList.add("history-id");

            entry.appendChild(date);
            entry.appendChild(content);
            entry.appendChild(id);

            parent.appendChild(entry);
        })
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