document.addEventListener("DOMContentLoaded", async function(event) {
    document.getElementById("submit-text").addEventListener("click", async function(event) {
        try{
            const original_text = document.getElementById("original-text").value;
            const src_lang = document.getElementById("source-languages").value;
            const dest_lang = document.getElementById("dest-languages").value;
            console.log(original_text, src_lang, dest_lang)
            const response = await fetch("/translate-text", {
                method : "POST",
                headers : {
                    "Content-Type" : "application/json",
                    "X-CSRF-TOKEN" : localStorage.getItem("X-CSRF-TOKEN"),
                    "X-CLIENT-TYPE" : "web"
                },
                body : JSON.stringify({text : original_text, src : src_lang, dest : dest_lang})
            });

            if(!response.ok){
                const statusCode = response.status;
                const statusText = response.statusText;
                throw new Error(`Server Error. Status: ${statusCode} ${statusText}`);
            }

            response.headers.forEach((key, value) => {
                if ("/x-csrf-token/i".test(key)){
                    localStorage.setItem("X-CSRF-TOKEN", value)
                }
            })

            const data = await response.json();
            let translated_textbox = document.getElementById("translated-text");
            translated_textbox.innerText = data["translated-text"];
        }
        catch(error){
            console.error("An Error Occured\n" + error)
        }
    })
})