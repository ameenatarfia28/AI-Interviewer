import os
import time

from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# GEMINI MODELS
# =========================================================

# Fast primary model
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Fallback model if the primary model is temporarily unavailable
GEMINI_FALLBACK_MODELS = [
    "gemini-3.6-flash",
]


# =========================================================
# GET GEMINI API KEY
# =========================================================

def get_gemini_api_key():
    """
    Get Gemini API key.

    Local:
        Reads GEMINI_API_KEY from .env

    Streamlit Cloud:
        Reads GEMINI_API_KEY from Streamlit Secrets
    """

    # -----------------------------------------------------
    # Try environment variable first
    # -----------------------------------------------------

    key = os.getenv("GEMINI_API_KEY")

    if key:
        return key


    # -----------------------------------------------------
    # Try Streamlit Secrets
    # -----------------------------------------------------

    try:

        import streamlit as st

        key = st.secrets.get(
            "GEMINI_API_KEY"
        )

    except Exception:

        key = None


    # -----------------------------------------------------
    # Key not found
    # -----------------------------------------------------

    if not key:

        raise RuntimeError(
            "GEMINI_API_KEY is not configured.\n\n"
            "For local development:\n"
            "Add GEMINI_API_KEY to your .env file.\n\n"
            "For Streamlit Cloud:\n"
            "Add GEMINI_API_KEY under App Settings → Secrets."
        )


    return key


# =========================================================
# QUOTA / RATE LIMIT ERROR
# =========================================================

def is_quota_error(error):
    """
    Detect Gemini quota / rate-limit errors.
    """

    message = str(error).lower()

    return (
        "429" in message
        or "quota" in message
        or "rate limit" in message
        or "resource exhausted" in message
        or "too many requests" in message
    )


# =========================================================
# SERVICE UNAVAILABLE ERROR
# =========================================================

def is_service_unavailable_error(error):
    """
    Detect temporary Gemini server-side errors.

    Examples:
        500
        502
        503
        504
    """

    message = str(error).lower()

    return (
        "500" in message
        or "502" in message
        or "503" in message
        or "504" in message
        or "service unavailable" in message
        or "currently experiencing high demand" in message
        or "temporarily overloaded" in message
        or "unavailable" in message
    )


# =========================================================
# GEMINI REQUEST WITH RETRY + FALLBACK
# =========================================================

def generate_with_fallback(
    client,
    contents,
    config=None
):
    """
    Send a request to Gemini.

    Flow:

        Primary model
             ↓
        Temporary error?
             ↓
        Short retry
             ↓
        Fallback model
             ↓
        Response
    """

    request_config = config or {}

    models = [
        GEMINI_MODEL,
        *GEMINI_FALLBACK_MODELS
    ]

    last_error = None


    # =====================================================
    # TRY MODELS
    # =====================================================

    for model_index, model in enumerate(models):

        # -------------------------------------------------
        # Each model gets at most 2 attempts
        # -------------------------------------------------

        for attempt in range(2):

            try:

                print(
                    f"[GEMINI] Request using model: "
                    f"{model} | attempt: {attempt + 1}"
                )


                response = client.models.generate_content(

                    model=model,

                    contents=contents,

                    config=request_config
                )


                print(
                    f"[GEMINI] Success using model: {model}"
                )

                return response


            except Exception as error:

                last_error = error


                print(
                    f"[GEMINI] Error using {model}: "
                    f"{error}"
                )


                # =========================================
                # NON-SERVER ERROR
                # =========================================

                if not is_service_unavailable_error(error):

                    raise


                # =========================================
                # PRIMARY MODEL FAILED
                # =========================================

                if model_index < len(models) - 1:

                    print(
                        f"[GEMINI] {model} unavailable. "
                        f"Switching to fallback model..."
                    )

                    break


                # =========================================
                # FINAL MODEL RETRY
                # =========================================

                if attempt == 0:

                    wait_time = 1.5

                    print(
                        f"[GEMINI] Retrying in "
                        f"{wait_time} seconds..."
                    )

                    time.sleep(
                        wait_time
                    )


    # =====================================================
    # ALL MODELS FAILED
    # =====================================================

    if last_error:

        raise last_error


    raise RuntimeError(
        "Gemini request failed without a response."
    )