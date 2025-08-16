FROM mcr.microsoft.com/dotnet/runtime-deps:8.0
WORKDIR /app

ADD DiscordChatExporter.Cli /app/DiscordChatExporter.Cli
RUN chmod +x /app/DiscordChatExporter.Cli

RUN apt-get update && apt-get install -y curl unzip ca-certificates && \
    curl -L https://downloads.rclone.org/rclone-current-linux-amd64.zip -o rclone.zip && \
    unzip rclone.zip && mv rclone-*-linux-amd64/rclone /usr/local/bin/ && rm -rf rclone*

ADD entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
