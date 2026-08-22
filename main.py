from src.utils.audio import validate_audio_file, extract_audio_properties


def main():
    print("Hello from call-center-intelligence!")

    file = "test_audio/call_2.mp3"

    print(validate_audio_file(file))
    print(extract_audio_properties(file))


if __name__ == "__main__":
    main()
