document.addEventListener("DOMContentLoaded", async function(event){
        cookie = localStorage.getItem("X-CSRF-TOKEN");
        console.warn(cookie);

        if (!cookie){
            try{
                const response = await fetch("http://192.168.0.105:8080/get-csrf", {
                    method : "GET",
                    headers : {
                        "Content-Type" : "application/json",
                        "X-CLIENT-TYPE" : "web"
                    }
                });

                if(!response.ok){
                    throw new Error("CSRF issuance failed");
                }

                const csrfToken = response.headers.get("X-CSRF-TOKEN");
                if (csrfToken) {
                    localStorage.setItem("X-CSRF-TOKEN", csrfToken);
                } else {
                    throw new Error("CSRF Token not found!");
                }
            }
            catch(error){
                console.error(error)
            }

        }
})