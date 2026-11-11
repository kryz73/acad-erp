import strawberry
from typing import Optional, List
from datetime import time, date
from sqlmodel import select
from .model import Rooms as RoomModel, TimetableSlots as TimetableSlotModel
from core.security import IsAuthenticated, IsAdmin

@strawberry.type
class RoomType:
    id: int
    code: str
    building: Optional[str]
    capacity: int
    room_type: Optional[str]

@strawberry.type
class TimetableSlotType:
    id: int
    offering_id: int
    room_id: Optional[int]
    day_of_week: int
    start_time: time
    end_time: time
    effective_from: date
    effective_to: Optional[date]

@strawberry.type
class SchedulingQuery:
    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_room(self, info: strawberry.Info, id: int) -> Optional[RoomType]:
        session = info.context["session"]
        r = session.get(RoomModel, id)
        return RoomType(**r.dict()) if r else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_rooms(self, info: strawberry.Info) -> List[RoomType]:
        session = info.context["session"]
        rooms = session.exec(select(RoomModel)).all()
        return [RoomType(**r.dict()) for r in rooms]

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_timetable_slot(self, info: strawberry.Info, id: int) -> Optional[TimetableSlotType]:
        session = info.context["session"]
        ts = session.get(TimetableSlotModel, id)
        return TimetableSlotType(**ts.dict()) if ts else None

    @strawberry.field(permission_classes=[IsAuthenticated])
    def get_timetable_slots(self, info: strawberry.Info, offering_id: Optional[int] = None) -> List[TimetableSlotType]:
        session = info.context["session"]
        query = select(TimetableSlotModel)
        if offering_id is not None:
            query = query.where(TimetableSlotModel.offering_id == offering_id)
        slots = session.exec(query).all()
        return [TimetableSlotType(**s.dict()) for s in slots]

@strawberry.type
class SchedulingMutation:
    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_room(self, info: strawberry.Info, code: str, capacity: int, building: Optional[str] = None, room_type: Optional[str] = None) -> RoomType:
        session = info.context["session"]
        new_room = RoomModel(code=code, capacity=capacity, building=building, room_type=room_type)
        session.add(new_room)
        session.commit()
        session.refresh(new_room)
        return RoomType(**new_room.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def create_timetable_slot(self, info: strawberry.Info, offering_id: int, day_of_week: int, start_time: time, end_time: time, effective_from: date, room_id: Optional[int] = None, effective_to: Optional[date] = None) -> TimetableSlotType:
        session = info.context["session"]
        new_slot = TimetableSlotModel(offering_id=offering_id, day_of_week=day_of_week, start_time=start_time, end_time=end_time, effective_from=effective_from, room_id=room_id, effective_to=effective_to)
        session.add(new_slot)
        session.commit()
        session.refresh(new_slot)
        return TimetableSlotType(**new_slot.dict())

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_room(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        r = session.get(RoomModel, id)
        if r:
            session.delete(r)
            session.commit()
            return True
        return False

    @strawberry.mutation(permission_classes=[IsAuthenticated, IsAdmin])
    def delete_timetable_slot(self, info: strawberry.Info, id: int) -> bool:
        session = info.context["session"]
        s = session.get(TimetableSlotModel, id)
        if s:
            session.delete(s)
            session.commit()
            return True
        return False
