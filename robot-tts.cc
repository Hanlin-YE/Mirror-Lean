/*
 * robot-tts - tiny C++ helper that speaks text through the Unitree G1 stock
 * audio service (AudioClient::TtsMaker).
 *
 * Build on the robot inside the unitree_sdk2 tree, then call from
 * robot-speaker-server.py for the /speak-text endpoint.
 */
#include <unitree/robot/channel/channel_factory.hpp>
#include <unitree/robot/g1/audio/g1_audio_client.hpp>

#include <cstdlib>
#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: " << argv[0] << " <network_interface> <text> [speaker_id]\n"
                  << "  speaker_id: 0 = Chinese/Auto (default), 1 = English\n";
        return 1;
    }

    const std::string iface = argv[1];
    const std::string text  = argv[2];
    int speaker_id = 0;
    if (argc >= 4) {
        speaker_id = std::atoi(argv[3]);
    }

    try {
        unitree::robot::ChannelFactory::Instance()->Init(0, iface);
        unitree::robot::g1::AudioClient client;
        client.Init();
        client.SetTimeout(10.0f);

        int ret = client.TtsMaker(text, speaker_id);
        if (ret != 0) {
            std::cerr << "TtsMaker failed with code " << ret << "\n";
            return 2;
        }
        std::cout << "ok\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "robot-tts exception: " << e.what() << "\n";
        return 3;
    }
}
