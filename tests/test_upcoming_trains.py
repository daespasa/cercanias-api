"""Tests para el endpoint de próximos trenes."""
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_upcoming_trains_with_time():
    """Test del endpoint con hora específica."""
    response = client.get("/stops/04040/upcoming?current_time=10:00:00&limit=3")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "data" in data
    result = data["data"]
    
    assert result["stop_id"] == "04040"
    assert result["stop_name"] == "Zaragoza Delicias"
    assert result["current_time"] == "10:00:00"
    assert "departures" in result
    assert "arrivals" in result
    assert isinstance(result["departures"], list)
    assert isinstance(result["arrivals"], list)
    
    # Verificar estructura de las salidas
    if result["departures"]:
        train = result["departures"][0]
        assert "trip_id" in train
        assert "route_short_name" in train
        assert "scheduled_time" in train
        assert "minutes_until" in train
        assert isinstance(train["minutes_until"], int)
        assert train["minutes_until"] >= 0
    
    print(f"✅ Test passed - Found {len(result['departures'])} departures and {len(result['arrivals'])} arrivals")


def test_upcoming_trains_current_time():
    """Test del endpoint sin especificar hora (usa hora actual)."""
    response = client.get("/stops/04040/upcoming?limit=5")
    
    assert response.status_code == 200
    data = response.json()
    
    result = data["data"]
    assert result["stop_id"] == "04040"
    assert result["current_time"] is not None
    assert ":" in result["current_time"]  # Formato HH:MM:SS
    
    print(f"✅ Test passed - Current time: {result['current_time']}")


def test_upcoming_trains_nonexistent_stop():
    """Test con parada que no existe."""
    response = client.get("/stops/99999/upcoming?current_time=10:00:00")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Stop not found"
    
    print("✅ Test passed - 404 for nonexistent stop")


def test_upcoming_trains_early_morning():
    """Test con hora temprana de la mañana."""
    response = client.get("/stops/04040/upcoming?current_time=06:00:00&limit=2")
    
    assert response.status_code == 200
    data = response.json()
    result = data["data"]
    
    assert result["stop_id"] == "04040"
    assert result["current_time"] == "06:00:00"
    
    # Debería haber trenes en la mañana
    if result["departures"]:
        first_train = result["departures"][0]
        print(f"  First departure: {first_train['scheduled_time']} ({first_train['minutes_until']} min)")
    
    print("✅ Test passed - Early morning schedule")


def test_upcoming_trains_structure():
    """Test detallado de la estructura de respuesta."""
    response = client.get("/stops/04040/upcoming?current_time=14:00:00&limit=1")
    
    assert response.status_code == 200
    data = response.json()
    result = data["data"]
    
    # Verificar estructura completa
    required_fields = ["stop_id", "stop_name", "current_time", "departures", "arrivals"]
    for field in required_fields:
        assert field in result, f"Missing field: {field}"
    
    # Verificar estructura de los trenes si hay datos
    if result["departures"]:
        train = result["departures"][0]
        train_fields = [
            "trip_id", "route_short_name", "route_long_name", 
            "trip_headsign", "direction_id", "scheduled_time", 
            "minutes_until", "stop_sequence"
        ]
        for field in train_fields:
            assert field in train, f"Missing train field: {field}"
    
    print("✅ Test passed - Response structure validated")
