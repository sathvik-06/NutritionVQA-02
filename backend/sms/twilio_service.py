import logging
from twilio.rest import Client
from config.settings import settings

logger = logging.getLogger("sms")

class TwilioService:
    def __init__(self):
        self.client = None
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                logger.info("Twilio client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")

    def _format_e164(self, number: str) -> str:
        """Ensure phone number is in E.164 format for Twilio."""
        # Strip all non-digit characters
        digits = "".join(filter(str.isdigit, number))
        
        # If it's exactly 10 digits, assume Indian number and prepend +91
        if len(digits) == 10:
            return f"+91{digits}"
        # If it starts with 91 and is 12 digits, just add +
        elif len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"
        # If it already has a +, return as-is
        elif number.startswith("+"):
            return number
        # Fallback: prepend +
        else:
            return f"+{digits}"

    async def send_otp(self, to_number: str, otp: str):
        if not self.client:
            logger.warning("Twilio client not initialized. Cannot send OTP.")
            return False
        
        formatted = self._format_e164(to_number)
        logger.info(f"📲 Sending OTP to formatted number: {formatted}")
        
        try:
            message = self.client.messages.create(
                body=f"Your NutritionVQA verification code is: {otp}. Do not share this with anyone.",
                from_=settings.TWILIO_PHONE_NUMBER,
                to=formatted
            )
            logger.info(f"OTP sent to {formatted}. Sid: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send OTP to {formatted}: {e}")
            return False

twilio_service = TwilioService()
