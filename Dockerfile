FROM mcr.microsoft.com/dotnet/runtime-deps:8.0
WORKDIR /app

RUN apt-get update && apt-get install -y curl unzip ca-certificates && \
    curl -L https://github.com/Tyrrrz/DiscordChatExporter/releases/latest/download/DiscordChatExporter.Cli.linux-x64.zip -o dce.zip && \
    unzip dce.zip && \
    chmod +x DiscordChatExporter.Cli && \
    rm dce.zip && \
    curl -L https://downloads.rclone.org/rclone-current-linux-amd64.zip -o rclone.zip && \
    unzip rclone.zip && mv rclone-*-linux-amd64/rclone /usr/local/bin/ && rm -rf rclone*

ADD entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
