document.addEventListener("DOMContentLoaded", async function(event) {
    const audio_dropper = document.getElementById("audio-dropper");
    const audio_label = document.getElementById("audio-label").querySelector("span");

    audio_dropper.addEventListener("change", function(event){
        const fileName = audio_dropper.files[0]?.name || "Upload Audio File";
        audio_label.innerText = fileName;
    })

    document.getElementById("submit-audio").addEventListener("click", async function(event){
        try{
            if(document.getElementById("audio-dropper").files.length !== 1){
                throw new Error("Only one file can be processed at a time")
            }

            let output_box = document.getElementById("transcription-output");
            let confidence_box = document.getElementById("confidence");
            output_box.innerText = "";
            confidence_box.innerText = "";
            
            const file = document.getElementById("audio-dropper").files[0];
            if (!file){
                throw new Error("File Not Found :(");
            }

            const extension = file.name.split(".").pop().toLowerCase();
            if(!["mp3", "aac", "wav", "ogg"].includes(extension)){
                alert("Invalid file extension chosen");
                return;
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


            output_box.innerText = transcript;
            confidence_box.innerText = `Confidence: ${(confidence*100).toFixed(2)}%`;
        }
        catch (error){
            console.error("Error ", error);
        }
    })
})