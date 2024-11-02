document.addEventListener("DOMContentLoaded", function (event) {
        const authType = window.location.pathname.split("/").slice(1);
        const subButton = document.getElementById("submission-btn");
        if (subButton === undefined || subButton === null) {
            throw new Error("DOM Integrity Error");
        }

        subButton.addEventListener("click", async function (event) {

            const identity = document.getElementById("email_id")?.value.trim();
            const password = document.getElementById("password")?.value.trim();
            const cpassword = document.getElementById("cpassword")?.value.trim();

            const authFormData = { identity, pass: password };
        
            if (authType !== "login") {
                authFormData.cpass = cpassword;
            }
            try{
                const response = await fetch("/", {
                    headers : {
                        "Content-Type" : "application/json",
                        "Sub" : "babel-auth-client"
                    },
                    method : "POST",
                    body : authFormData
                });
                
                if(!response.ok){
                    const data = await response.json();
                    throw new Error(`${data.message}\nCode: ${response.status}`)
                }
                const data = await response.json();
            }
            catch(error){
                console.error("Submission Error: ", error)
            }
        })
})