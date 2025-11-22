from app.core.gtfs_manager import gtfs_manager
from pandas import DataFrame

gtfs_manager.data = {}
gtfs_manager.data['stop_times'] = DataFrame([
    {'trip_id':'t1','arrival_time':'08:00:00','departure_time':'08:00:00','stop_id':'S1','stop_sequence':1},
    {'trip_id':'t2','arrival_time':'09:00:00','departure_time':'09:00:00','stop_id':'S1','stop_sequence':1},
])
gtfs_manager.data['trips'] = DataFrame([
    {'trip_id':'t1','service_id':'svc1','route_id':'40T0001C1'},
    {'trip_id':'t2','service_id':'svc2','route_id':'40T0001C1'},
])
print('get_schedule:', gtfs_manager.get_schedule(stop_id='S1', limit=1))
