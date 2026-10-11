from chat_controller import ChatController


def main():
    print("=" * 60)
    print("       STUDENT AI DASHBOARD")
    print("       Python + MySQL Backend")
    print("=" * 60)

    controller = ChatController()

    while True:
        print()

        question = input(
            "Ask your question (type 'exit' to stop): "
        )

        if question.lower().strip() == "exit":
            print("\nThank you!")
            break

        response = controller.ask(question)

        print("\n================ ANSWER ================")
        print(response["answer"])

        print("\n================ SOURCES ================")

        if response["sources"]:
            for source in response["sources"]:
                print(
                    f"- {source['category']} | "
                    f"{source['title']} | "
                    f"{source['source']}"
                )
        else:
            print("No sources found.")


if __name__ == "__main__":
    main()
