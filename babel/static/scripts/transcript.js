document.addEventListener("DOMContentLoaded", async function(event) {
    document.getElementById("submit-audio").addEventListener("click", async function(event){
        try{
            const file = document.getElementById("audio-dropper").files[0];
            if (!file){
                throw new Error("File Not Found :(");
            }
            console.log("Selected File: " + file)
            let audioForm = new FormData();
            audioForm.append("audio-file", file);

            const response = await fetch("/transcript-speech", {
                method : "POST",
                body : audioForm
            });

            if(!response.ok){
                throw new Error(`An error occured in getting the transcript:\nStatus: ${response.status}\nMessage: ${response.statusText}`);
            }

            const data = await response.json();
            const transcript = data["text"];
            const confidence = data["confidence"];

            if (transcript === undefined || confidence === undefined){
                throw new Error("Unexpected response format :(");
            }

            let output_box = document.getElementById("transcription-output");
            let confidence_box = document.getElementById("confidence");
            output_box.innerText = transcript;
            confidence_box.innerText = confidence;
        }
        catch (error){
            console.error("Error ", error);
        }
    })
})