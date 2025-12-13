import joblib
import pandas as pd
import requests
import time
from typing import Dict, Any, List


class ModelService:
    # Map ship type -> model file
    # Map ship type -> model file (phù hợp với các file .pkl hiện có trong /models)
    SHIP_MODEL_MAP = {
        "CETO": "models/ceto_stacked.pkl",
        "POSEIDON": "models/poseidon_best_model-001.pkl",
        "TRITON": "models/triton_best_model.pkl",
    }

    # Feature order EXACTLY like your test script
    FEATURES = [
        "Ship_SpeedOverGround",
        "Environment_SeaFloorDepth",
        "Weather_Temperature2M",
        "Weather_OceanCurrentVelocity",
        "Weather_WindSpeed10M",
        "Weather_WaveHeight",
        "Weather_WavePeriod"
    ]

    def __init__(self):
        self.model = None
        self.current_ship_type = None
        
        # Embedding server config
        self.LM_STUDIO_URL = "http://localhost:1234/v1/embeddings"
        self.EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"


    # --- Load model theo loại tàu ---
    def load_model_for_ship(self, ship_type: str):
        st = ship_type.upper()
        if st not in self.SHIP_MODEL_MAP:
            raise ValueError(f"Unknown ship type: {st}")

        path = self.SHIP_MODEL_MAP[st]
        self.model = joblib.load(path)
        self.current_ship_type = st
        print(f"Loaded model for {st} -> {path}")

        # Debug: xem model được train với bao nhiêu features
        if hasattr(self.model, "feature_names_in_"):
            print("Model feature names:", list(self.model.feature_names_in_))


    # --- Chuẩn hóa input ---
    def prepare_features(self, params: Dict[str, Any]) -> pd.DataFrame:
        df = pd.DataFrame([[  
            params["Ship_SpeedOverGround"],
            params["Environment_SeaFloorDepth"],
            params["Weather_Temperature2M"],
            params["Weather_OceanCurrentVelocity"],
            params["Weather_WindSpeed10M"],
            params["Weather_WaveHeight"],
            params["Weather_WavePeriod"],
        ]], columns=self.FEATURES)

        print("INPUT FED TO MODEL:")
        print(df)

        return df


    # --- Predict ---
    def predict(self, params: Dict[str, Any]) -> float:
        st = params["ship_type"].upper()

        # load model nếu chuyển loại tàu
        if st != self.current_ship_type:
            self.load_model_for_ship(st)

        X = self.prepare_features(params)
        pred = self.model.predict(X)
        return float(pred[0])


    # --- Lấy embedding từ LM Studio ---
    def get_embedding(self, text: str, retry_count: int = 3) -> List[float]:
        for attempt in range(retry_count):
            try:
                response = requests.post(
                    self.LM_STUDIO_URL,
                    json={
                        "model": self.EMBEDDING_MODEL,
                        "input": text,
                    },
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data["data"][0]["embedding"]

                    print(f"Embedded text (len {len(text)} chars) -> dim {len(embedding)}")
                    return embedding

                else:
                    print(f"Error: {response.status_code} - {response.text}")

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < retry_count - 1:
                    time.sleep(2)

        raise Exception(f"Failed to get embedding after {retry_count} attempts")


# Create global instance
model_service = ModelService()
