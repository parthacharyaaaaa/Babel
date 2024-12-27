document.addEventListener("DOMContentLoaded", async function(event){
        token = localStorage.getItem("X-CSRF-TOKEN");

        if (!token){
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