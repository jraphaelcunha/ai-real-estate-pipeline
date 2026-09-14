
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from openai import APIError, AuthenticationError, RateLimitError

from src.config import settings
from src.domain.schemas import ActionEnum, PropertyAnalysis, PropertyInput
from src.utils.logger import get_logger

logger = get_logger("analyzer")

class RealEstateAnalyzer:
    """
    Service to analyze real estate properties using LLM or Mock Data.
    """
    
    def __init__(self):
        self.mock_mode = False
        self.llm = None
        
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not found in settings. Enabling MOCK MODE.")
            self.mock_mode = True
        else:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o-mini",
                    api_key=settings.OPENAI_API_KEY,
                    temperature=0
                )
            except Exception as e:
                logger.error(f"Failed to initialize ChatOpenAI: {e}. Enabling MOCK MODE.")
                self.mock_mode = True

    def analyze_property(self, property_data: PropertyInput) -> PropertyAnalysis | None:
        """
        Analyzes a property to determine investment viability.
        Returns simulated data if in mock mode or if API fails.
        """
        logger.info(f"Starting analysis for property: {property_data.address}")
        
        if self.mock_mode:
            return self._get_mock_analysis()

        # Define Prompt
        system_msg = (
            "You are a Senior Real Estate Underwriter. "
            "Analyze the provided property data for investment viability in the Dallas market. "
            "Be strict and critical. "
            "Financial Rules: "
            "1. ARV (After Repair Value) MUST be exactly 1.3 * Price. "
            "2. Renovation Cost MUST be exactly 0.15 * Price. "
            "Output these values precisely."
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_msg),
            ("user", "Address: {address}\nPrice: {price}\nDescription: {description}\nLink: {link}")
        ])

        try:
            # Configure Structured Output
            structured_llm = self.llm.with_structured_output(PropertyAnalysis)
            chain = prompt | structured_llm
            
            result = chain.invoke({
                "address": property_data.address,
                "price": str(property_data.price),
                "description": property_data.raw_description,
                "link": str(property_data.link)
            })
            
            logger.info("Analysis successful.")
            return result

        except (AuthenticationError, RateLimitError, APIError) as e:
            logger.warning(f"OpenAI API Error ({type(e).__name__}): {e}. Falling back to MOCK DATA.")
            return self._get_mock_analysis()
            
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {e}")
            # Decide if we want to fallback on generic errors too. 
            # For now, let's fallback to mock data to keep the pipeline moving as per instruction.
            logger.warning("Falling back to MOCK DATA due to unexpected error.")
            return self._get_mock_analysis()

    def _get_mock_analysis(self) -> PropertyAnalysis:
        logger.warning("Returning MOCK analysis data.")
        return PropertyAnalysis(
            viability_score=85,
            summary="Mock analysis for testing Monday integration. Property appears undervalued with good rental potential.",
            risk_factors=["High foundation repair costs possible", "Flood zone proximity"],
            recommended_action=ActionEnum.BUY,
            arv=350000.00,
            renovation_cost=45000.00
        )
