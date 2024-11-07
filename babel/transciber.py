import requests, time, os
from babel.config import aai_config
from typing import Union, Optional

from babel.auxillary.errors import Unexpected_Request_Format, Unexpected_Response_Format, API_TIMEOUT_ERROR

def upload_audio(headers : dict, file_path : str) -> Optional[str]:
    """Uploads audio file to AssemblyAI

    params:
    file_path: Path of the audio file
    headers: dictionary containting headers

    returns:
    URL of the audio saved on AssemblyAI's servers
    """
    if not isinstance(file_path, str):
        raise TypeError("Filepath must be a string instance")
    if not os.path.isfile(file_path):
        raise FileNotFoundError("Filepath not found")
    if not file_path.endswith((".mp3", ".wav", ".aac")):
        raise ValueError("Filepath must be an audio file, with format as mp3, aac, or wav")
    
    # try:
    with open(file_path, 'rb') as file:
        response = requests.post(aai_config.UPLOAD_URL, headers=headers, files={'file': file})
    response.raise_for_status()
    print(response.json())
    return response.json()['upload_url']

def transcribe_audio(headers : dict, audio_url : str) -> Union[str, int]:
    """Submits transcription request and retrieves the trancript ID

    params:
    audio_url: URL obtained from upload_audio()
    headers: dictionary containting headers
    
    returns:
    Transcript ID of the requested transcription to AssembyAI
    """
    if not (isinstance(audio_url, str) and isinstance(headers, dict)):
        raise TypeError("Audio URL must be a string instance")
    
    try:
        response = requests.post(aai_config.TRANSCRIPT_URL, json={'audio_url': audio_url}, headers=headers)
        response.raise_for_status()
        return response.json()['id']
    except requests.HTTPError as e:
        print("AssemblyAI responded with an error: {}".format(response.status_code))
    except KeyError as e:
        print("Unexpected response format from AssemblyAI (Key 'id' not found in JSON serialized form)\n{}".format(response.json()))

def check_transcription_status(headers : dict, transcript_id : Union[str, int], trancript_url : str = aai_config.TRANSCRIPT_URL) -> str:
    """Checks the status of the transcription"""

    if not (isinstance(trancript_url, str) and isinstance(transcript_id, (int, str)) and isinstance(headers, dict)):
        raise TypeError("Invalid types provided")
    
    try:
        response = requests.get(f'{aai_config.TRANSCRIPT_URL}/{transcript_id}', headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        print("AssemblyAI responded with an error: {}".format(response.status_code))
    except KeyError as e:
        print("Unexpected response format from AssemblyAI (Key 'status' not found in JSON serialized form)\n{}".format(response.json()))

def getAudioTranscription(filepath : str, api_key : str = aai_config.AAI_API_KEY, max_attempts : int = 50, poll_interval : int = 4) -> dict:
    ''' ### Performs the actual transcription for a given audio file

    params:

    filepath: The path of the audio file to be transcribed
    key: The API key for Assembly AI
    max_attempts: Number of times to poll AssemblyAI's API endpoint before exiting the function
    poll_interval: Time interval to wait between consecutive polls
    
    returns: dictionary object with text attribute set to the transcripted text and confidence attribute set to the average confidence of the words
    '''
    #Initialize headers
    if not api_key.isalnum():
        raise ValueError(f"ASSEMBLY-AI API KEY IS INVALID. MUST BE STRINCTLY ALPHA-NUMERIC, NOT {api_key}")

    headers = {
        "Authorization" : api_key,
        "Content-Type" : "application/json"
    }

    audio_url = upload_audio(headers, filepath)
    if audio_url is None:
        raise requests.HTTPError("Max tries exceeded with AssemblyAI")
    
    transcription_id = transcribe_audio(headers, audio_url)

    
    for _ in range(max_attempts):
        result = check_transcription_status(headers, transcription_id)
        if result['status'] == "completed":
            print("Transcription Done\n")
            overall_confidence = sum(item['confidence'] for item in result['words']) / len(result['words'])

            return {"text" : result["text"], "confidence" : overall_confidence}
        elif result['status'] == "error":
            print("Transcription Failed")
            print(result)
            raise RuntimeError("Transcription Failed")
        
        time.sleep(poll_interval)
    
    #Loop exit indicates overflow of maximum attempts
    raise API_TIMEOUT_ERROR(endpoint=aai_config.TRANSCRIPT_URL)