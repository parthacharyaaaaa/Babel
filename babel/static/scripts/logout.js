document.addEventListener("DOMContentLoaded", function(event){
    const logoutBtn = document.getElementById("logout-btn");
    logoutBtn.addEventListener("click", async function(event){
        try{
            const response = await fetch(`http://${window.location.hostname}:8080/purge-family`, {
                headers : {
                    "Content-Type" : "application/json",
                    "X-CLIENT-TYPE" : "web",
                    "X-CSRF-TOKEN" : localStorage.getItem("X-CSRF-TOKEN")
                },
                method : "GET",
                credentials : "include"
            });

            if (!response.ok){
                throw new Error(`${response.status}: ${response.statusText}`)
            }

            alert("You have logged out successfully");
            window.location.href = "/";

        }
        catch(error){
            console.error(error)
        }

    })
})