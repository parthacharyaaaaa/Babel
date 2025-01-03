document.addEventListener("DOMContentLoaded", async function (event) {
    try {
        const response = await fetch("/fetch-languages", {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "X-CSRF-TOKEN" : localStorage.getItem("X-CSRF-TOKEN"),
                "X-CLIENT-TYPE" : "web"
            },
            credentials : "include"
        });
        const csrfToken = response.headers.get("X-CSRF-TOKEN");
        if (csrfToken) {
            localStorage.setItem("X-CSRF-TOKEN", csrfToken);
        }

        if(!response.ok){
            const statusCode = response.status;
            const statusText = response.statusText;
            throw new Error(`Failed to fetch available languages from server. Status: ${statusCode} ${statusText}`);
        }


        const available_languages = await response.json();
        let languages_lists = document.querySelectorAll(".language-list");

        languages_lists.forEach(languages_list => {
            languages_list.innerHTML = "";

            const is_destination_lang = languages_list.id === "dest-language";
            Object.entries(available_languages).forEach(([key, value], index) => {
                let lang = document.createElement("option");
                if(is_destination_lang && key === "auto"){
                    return;
                }
                else{
                    lang.value = key;
                    lang.text = key + " - " + value;
                    lang.id = `${index+1}`;
        
                    languages_list.appendChild(lang);
                }
            });
        })
    }

    catch(error){
        console.error("Error: " + error.message)
    }
});