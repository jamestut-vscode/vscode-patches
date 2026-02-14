FROM alpine:latest
RUN apk add --no-cache curl tar
RUN curl -L -o /tmp/patchelf.tar.gz https://github.com/NixOS/patchelf/releases/download/0.18.0/patchelf-0.18.0-aarch64.tar.gz \
	&& tar -xzf /tmp/patchelf.tar.gz -C /tmp \
	&& mv /tmp/bin/patchelf /usr/local/bin/patchelf \
	&& rm -rf /tmp/patchelf*
