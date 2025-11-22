from google.transit import gtfs_realtime_pb2
from app.core.rt_fetcher import rt_fetcher
from app.core.gtfs_manager import gtfs_manager


def make_vehicle_entity(trip_id: str = "T1", lat: float = 40.0, lon: float = -3.0):
    feed = gtfs_realtime_pb2.FeedMessage()
    e = feed.entity.add()
    e.id = "v1"
    vp = e.vehicle
    vp.trip.trip_id = trip_id
    vp.position.latitude = lat
    vp.position.longitude = lon
    vp.current_status = gtfs_realtime_pb2.VehiclePosition.IN_TRANSIT_TO
    return feed


def make_trip_update_entity(trip_id: str = "T1"):
    feed = gtfs_realtime_pb2.FeedMessage()
    e = feed.entity.add()
    e.id = "u1"
    tu = e.trip_update
    tu.trip.trip_id = trip_id
    return feed


def make_alert_entity():
    feed = gtfs_realtime_pb2.FeedMessage()
    e = feed.entity.add()
    e.id = "a1"
    alert = e.alert
    # add a simple translation for header_text
    alert.header_text.translation.add().text = "Test alert"
    alert.description_text.translation.add().text = "Description"
    return feed


def test_parse_vehicles():
    feed = make_vehicle_entity()
    # clear any previous data
    gtfs_manager.rt_vehicles = []
    rt_fetcher._parse_vehicles(feed)
    assert len(gtfs_manager.rt_vehicles) == 1
    v = gtfs_manager.rt_vehicles[0]
    assert v.trip.trip_id == "T1"


def test_parse_trip_updates():
    feed = make_trip_update_entity("TU1")
    gtfs_manager.rt_trip_updates = []
    rt_fetcher._parse_trip_updates(feed)
    assert len(gtfs_manager.rt_trip_updates) == 1
    u = gtfs_manager.rt_trip_updates[0]
    assert u.trip.trip_id == "TU1"


def test_parse_alerts():
    feed = make_alert_entity()
    gtfs_manager.rt_alerts = []
    rt_fetcher._parse_alerts(feed)
    assert len(gtfs_manager.rt_alerts) == 1
    a = gtfs_manager.rt_alerts[0]
    assert a.header_text.translation[0].text == "Test alert"
