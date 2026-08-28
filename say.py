import sys
from unitree_sdk2py.core.channel import ChannelFactoryInitialize
from unitree_sdk2py.g1.audio.g1_audio_client import AudioClient

if __name__ == "__main__":
    iface = sys.argv[1] if len(sys.argv) > 1 else "eth0"
    text = sys.argv[2] if len(sys.argv) > 2 else "大家好，我是健身教练小G。我会陪你完成今天的训练，请站到我对面，跟随我的动作一起练习。"

    ChannelFactoryInitialize(0, iface)
    client = AudioClient()
    client.SetTimeout(10.0)
    client.Init()

    code = client.TtsMaker(text, 0)
    print("TtsMaker ret=%d" % code)
    if code == 0:
        print("PLAYING: " + text)
