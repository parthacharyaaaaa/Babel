async function checkExpiry(){
    try{
        const exp = localStorage.getItem("access_exp");
        const leeway = localStorage.getItem("leeway") !== null ? localStorage.getItem("leeway") : 0;
        const currentTime = Math.floor(Date.now() / 1000);
        if (exp != null && exp < currentTime - 120 - leeway){
            reauth();
        }
        else{
            setTimeout(() => checkExpiry(), 60000)
        }
    }
    catch(error){
        console.log("Error: " + error)
    }
}

async function reauth(){
    try{
        const response = await fetch("http://192.168.0.105:8080/reissue", {
                method : "GET",
                headers : {
                    "Content-Type" : "application/json"
                },
                credentials : "include"
            }
        );
        if(!response.ok){
            if (response.status === 401){
                alert("It seems there is an issue with your session. Please reauthenticate to continue using Babel. We apologize for the inconveninece. If this issue persists, contact support");
            }
            else{
                throw new Error(`${response.status}: Silent Reauthentication failed, details: ${response.statusText}`)
            }
        }

        const result = await response.json();
        if(aToken != result.expCredential){
            throw new Error("Authentication failed, please login again");
        }

        localStorage.setItem("access_exp", result.access_exp);
        localStorage.setItem("leeway", result.leeway !== undefined ? result.leeway : 0);
    }
    catch(error){
        throw error;
    }
}