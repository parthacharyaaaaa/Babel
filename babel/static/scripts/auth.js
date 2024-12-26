document.addEventListener("DOMContentLoaded", function (event) {
        const authType = window.location.pathname.split("/").slice(1)[0];
        const subButton = document.getElementById("submission-btn");
        if (subButton === undefined || subButton === null) {
            throw new Error("DOM Integrity Error");
        }

        subButton.addEventListener("click", async function (event) {

            const password = document.getElementById("password")?.value.trim();            
            const authFormData = { password: password };
            
            if (authType !== "login") {
                authFormData.email = document.getElementById("email_id")?.value.trim();
                authFormData.username = document.getElementById("username")?.value.trim();
                authFormData.cpassword = document.getElementById("cpassword")?.value.trim();
            }
            else{
                authFormData.identity = document.getElementById("identity")?.value.trim();
            }

            try{
                const response = await fetch(authType === "login"? "http://192.168.0.105:8080/login" : "http://192.168.0.105:8080/register", {
                    headers : {
                        "Content-Type" : "application/json",
                        "sub" : "babel-auth-client"
                    },
                    method : "POST",
                    body : JSON.stringify(authFormData),
                    credentials : "include"
                });
                
                if(!response.ok){
                    const data = await response.json();
                    throw new Error(`${data.message}\nCode: ${response.status}`)
                }
                const data = await response.json();
                alert(data.message);

                localStorage.setItem("access_exp", data.access_exp);
                localStorage.setItem("leeway", data.leeway !== undefined ? data.leeway : 0);

                window.location.href = window.location.host;
            }
            catch(error){
                console.error("Submission Error: ", error)
            }
        })
})