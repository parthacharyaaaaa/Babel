document.addEventListener("DOMContentLoaded", function(event){
    const logoutBtn = document.getElementById("logout-btn");
    logoutBtn.addEventListener("click", async function(event){
        try{
            const response = await fetch(`http://${window.location.hostname}:8080/purge-family`, {
                headers : {
                    "Content-Type" : "application/json",
                    "X-CSRF-TOKEN" : localStorage.getItem("X-CSRF-TOKEN"),
                    "X-CLIENT-TYPE" : "web"
                },
                method : "GET",
                credentials : "include"
            });

            if (!response.ok){
                throw new Error(`${response.status}: ${response.statusText}`)
            }
            localStorage.clear()
            alert("You have logged out successfully");
            window.location.href = "/";

        }
        catch(error){
            console.error(error)
        }

    })
})