from openai import OpenAI
from flask import current_app

class OpenAIService:
    def __init__(self):
        self.client = None
        try:
            from config import Config
            api_key = Config.OPENAI_API_KEY
            if api_key:
                self.client = OpenAI(api_key=api_key)
        except:
            pass
    
    def get_recommendations(self, temperature, light, moisture, moisture_status, role, age=None):
        """Generate product recommendations based on sensor data, user role, and age"""
        
        if not self.client:
            return {
                'recommendations': [
                    'Please configure OpenAI API key in environment variables',
                    'For oily hair: Use clarifying shampoo',
                    'For dry hair: Use moisturizing conditioner',
                    'For dense hair: Use volumizing products'
                ],
                'reasoning': 'OpenAI API key not configured'
            }
        
        try:
            age_info = ""
            if age:
                age_info = f"\nAge: {age} years old"
                if role == 'child':
                    if age < 3:
                        age_info += " (toddler - use gentle, tear-free products)"
                    elif age < 12:
                        age_info += " (child - use mild, safe products)"
                    else:
                        age_info += " (teenager - may need specialized products)"
                elif role in ['mother', 'father']:
                    if age < 30:
                        age_info += " (young adult)"
                    elif age < 50:
                        age_info += " (adult)"
                    else:
                        age_info += " (mature - may need age-appropriate products)"
            
            prompt = f"""Based on the following hair sensor data, provide personalized hair product recommendations:

Sensor Readings:
- Temperature: {temperature}°C (indicates scalp heat/irritation level)
- Light Sensor: {light} (indicates hair density - higher values mean denser hair)
- Moisture Level: {moisture}% (moisture reading)
- Moisture Status: {moisture_status} (oily/dry/normal)

User Role: {role} (mother/father/child){age_info}

Please provide:
1. 3-5 specific product recommendations (shampoo, conditioner, treatments) that are age-appropriate
2. Brief reasoning for each recommendation, considering both sensor data and age
3. Key beneficial ingredients/chemicals that should be in the products (e.g., keratin, biotin, argan oil, salicylic acid, etc.)
4. General hair care tips based on the readings and age

IMPORTANT: 
- For each product recommendation, provide a clear, searchable product name that can be used to search on Amazon.
- Consider age-appropriate products (e.g., gentle products for children, age-specific treatments for adults)
- Take into account that different ages may have different hair care needs
- List specific beneficial ingredients/chemicals that address the hair concerns indicated by the sensor data
- Explain why each ingredient is beneficial for the specific hair condition

Format your response as a JSON object with:
- "recommendations": array of objects, each with:
  - "name": clear product name (e.g., "Clarifying Shampoo for Oily Hair", "Moisturizing Conditioner")
  - "type": product type (e.g., "shampoo", "conditioner", "treatment")
  - "reason": brief explanation why this product is recommended (mention age if relevant)
  - "key_ingredients": array of key beneficial ingredients/chemicals in this product (e.g., ["salicylic acid", "tea tree oil", "niacinamide"])
- "beneficial_ingredients": array of objects, each with:
  - "name": ingredient/chemical name (e.g., "Keratin", "Biotin", "Argan Oil", "Salicylic Acid")
  - "benefit": brief explanation of why this ingredient is beneficial for the current hair condition
  - "found_in": what type of products typically contain this (e.g., "shampoos, conditioners, treatments")
- "tips": array of general hair care tips
- "reasoning": brief explanation of the analysis

Example format:
{{
  "recommendations": [
    {{
      "name": "Clarifying Shampoo for Oily Hair",
      "type": "shampoo",
      "reason": "Helps remove excess oil and buildup",
      "key_ingredients": ["salicylic acid", "tea tree oil", "niacinamide"]
    }}
  ],
  "beneficial_ingredients": [
    {{
      "name": "Salicylic Acid",
      "benefit": "Helps exfoliate scalp and remove excess oil and dead skin cells",
      "found_in": "shampoos, scalp treatments"
    }},
    {{
      "name": "Tea Tree Oil",
      "benefit": "Antimicrobial properties help control scalp oil production",
      "found_in": "shampoos, conditioners"
    }}
  ],
  "tips": ["Wash hair every other day", "Use lukewarm water"],
  "reasoning": "Based on high moisture readings indicating oily scalp"
}}
"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a hair care expert and cosmetic chemist providing personalized product recommendations and ingredient analysis based on sensor data. Always provide specific, scientifically-backed ingredient recommendations."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            result_text = response.choices[0].message.content
            
            # Try to parse as JSON, if not return as text
            try:
                import json
                return json.loads(result_text)
            except:
                return {
                    'recommendations': result_text.split('\n'),
                    'reasoning': 'AI-generated recommendations based on sensor data'
                }
                
        except Exception as e:
            return {
                'recommendations': [
                    f'Error generating recommendations: {str(e)}',
                    'For oily hair: Use clarifying shampoo',
                    'For dry hair: Use moisturizing conditioner'
                ],
                'reasoning': 'Error occurred'
            }
    
    def chat(self, message, sensor_data=None):
        """Handle chatbot queries about hair health"""
        
        if not self.client:
            return "I'm sorry, the AI service is not configured. Please set up your OpenAI API key."
        
        try:
            context = ""
            if sensor_data:
                context = f"""
Recent sensor readings:
- Temperature: {sensor_data.get('temperature', 'N/A')}°C
- Light (Density): {sensor_data.get('light', 'N/A')}
- Moisture: {sensor_data.get('moisture_status', 'N/A')}
"""
            
            prompt = f"""You are a helpful hair care assistant for a smart comb monitoring system. 
{context}
Answer the user's question about hair health, monitoring, or the smart comb system in a friendly and informative way.
Keep responses concise and practical."""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": message}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"I'm sorry, I encountered an error: {str(e)}. Please try again later."

