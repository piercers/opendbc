import copy

from openpilot.common.params import Params
from opendbc.car import Bus
from opendbc.car.subaru.values import CanBus, SubaruFlags


SNG_ACC_MIN_DIST = 3
SNG_ACC_MAX_DIST = 4.5
SNG_RESUME_FRAMES = 15
SNG_THROTTLE_PEDAL = 5


class SubaruStopAndGo:
  def __init__(self, CP):
    self.enabled = Params().get_bool("SubaruStopAndGo") and not (CP.flags & (SubaruFlags.GLOBAL_GEN2 | SubaruFlags.HYBRID))
    self.resume_frames_remaining = 0
    self.prev_close_distance = 0.0

  def update(self, CC, CS) -> bool:
    if not CC.enabled or not CC.hudControl.leadVisible:
      self.resume_frames_remaining = 0
      return False

    close_distance = CS.es_distance_msg["Close_Distance"]
    distance_increasing = close_distance > self.prev_close_distance
    in_resume_distance = SNG_ACC_MIN_DIST < close_distance < SNG_ACC_MAX_DIST
    should_resume = CS.out.standstill and in_resume_distance and distance_increasing

    if should_resume:
      self.resume_frames_remaining = SNG_RESUME_FRAMES

    send_resume = self.resume_frames_remaining > 0
    if send_resume:
      self.resume_frames_remaining -= 1

    self.prev_close_distance = close_distance
    return send_resume

  @staticmethod
  def create_throttle(packer, CP, throttle_msg, send_resume):
    if CP.flags & SubaruFlags.PREGLOBAL:
      signals = [
        "Throttle_Pedal", "Signal1", "Not_Full_Throttle", "Signal2", "Engine_RPM", "Off_Throttle", "Signal3",
        "Throttle_Cruise", "Throttle_Combo", "Throttle_Body", "Off_Throttle_2", "Signal4",
      ]
    else:
      signals = [
        "CHECKSUM", "Signal1", "Engine_RPM", "Neutral", "Throttle_Pedal", "Throttle_Cruise", "Throttle_Combo",
        "Signal3", "Off_Accel",
      ]

    values = {signal: throttle_msg[signal] for signal in signals}
    values["COUNTER"] = (throttle_msg["COUNTER"] + 1) % 0x10
    if send_resume:
      values["Throttle_Pedal"] = SNG_THROTTLE_PEDAL

    return packer.make_can_msg("Throttle", CanBus.camera, values)
