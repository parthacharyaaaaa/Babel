document.addEventListener("DOMContentLoaded", function (event) {
    const deleteBtn = document.getElementById("delete-btn");

    deleteBtn.addEventListener("click", async function (event) {
        // Add the password and confirm password pop-up here
        const modal = document.createElement("div");
        modal.style.position = "fixed";
        modal.style.top = "0";
        modal.style.left = "0";
        modal.style.width = "100%";
        modal.style.height = "100%";
        modal.style.backgroundColor = "rgba(0, 0, 0, 0.5)";
        modal.style.display = "flex";
        modal.style.justifyContent = "center";
        modal.style.alignItems = "center";
        modal.style.zIndex = "1000";

        // Create the content container
        const content = document.createElement("div");
        content.style.backgroundColor = "#fff";
        content.style.padding = "20px";
        content.style.borderRadius = "8px";
        content.style.width = "300px";
        content.style.textAlign = "center";

        // Create the title
        const title = document.createElement("h2");
        title.innerText = "Confirm Your Password";
        content.appendChild(title);

        // Create the first password input
        const password1 = document.createElement("input");
        password1.type = "password";
        password1.placeholder = "Enter password";
        password1.style.marginBottom = "10px";
        password1.style.padding = "8px";
        password1.style.width = "100%";
        password1.style.borderRadius = "4px";
        password1.style.border = "1px solid #ccc";
        content.appendChild(password1);

        // Create the second password input
        const password2 = document.createElement("input");
        password2.type = "password";
        password2.placeholder = "Confirm password";
        password2.style.marginBottom = "20px";
        password2.style.padding = "8px";
        password2.style.width = "100%";
        password2.style.borderRadius = "4px";
        password2.style.border = "1px solid #ccc";
        content.appendChild(password2);

        // Create the delete button
        const deleteAccountBtn = document.createElement("button");
        deleteAccountBtn.innerText = "I am ready to delete my Babel account";
        deleteAccountBtn.style.backgroundColor = "red";
        deleteAccountBtn.style.color = "white";
        deleteAccountBtn.style.padding = "10px";
        deleteAccountBtn.style.width = "100%";
        deleteAccountBtn.style.border = "none";
        deleteAccountBtn.style.borderRadius = "4px";
        deleteAccountBtn.style.cursor = "pointer";
        content.appendChild(deleteAccountBtn);

        // Create the cancel button
        const cancelBtn = document.createElement("button");
        cancelBtn.innerText = "Cancel";
        cancelBtn.style.backgroundColor = "gray";
        cancelBtn.style.color = "white";
        cancelBtn.style.padding = "10px";
        cancelBtn.style.width = "100%";
        cancelBtn.style.border = "none";
        cancelBtn.style.borderRadius = "4px";
        cancelBtn.style.marginTop = "10px";
        cancelBtn.style.cursor = "pointer";
        content.appendChild(cancelBtn);

        // Append content to modal
        modal.appendChild(content);

        // Append modal to body
        document.body.appendChild(modal);

        cancelBtn.addEventListener("click", function() {
            document.body.removeChild(modal);
        });

        deleteAccountBtn.addEventListener("click", async function(event){
            if(password1.value !== password2.value){
                alert("Passwords do not match");
                return;
            }

            try{
                const response = await fetch("/delete-account", {
                    method : "DELETE",
                    credentials : "include",
                    headers : {
                        "Content-Type" : "application/json"
                    },
                    body : JSON.stringify({password : password1.value})
                });
                
                if(response.status === 401){
                    alert("Incorrect Password");
                    return;
                }
                if(!response.ok){
                    throw new Error(`${response.status}: ${response.statusText}`);
                }

                localStorage.clear()
                alert("Account Deleted Successfully");
                window.location.href = "/";
            }
            catch(error){
                alert(error)
            }
        })

    })
})