FROM quay.io/rockylinux/rockylinux:9

# Rocky's minimal container ships coreutils-single. The labs intentionally use
# the full coreutils command set, so allow DNF to replace the slim package.
RUN dnf -y install --allowerasing \
      bash \
      coreutils \
      findutils \
      grep \
      gawk \
      sed \
      tar \
      gzip \
      procps-ng \
      shadow-utils \
      util-linux \
      sudo \
    && dnf clean all \
    && rm -rf /var/cache/dnf

RUN mkdir -p /submission /workspace /srv \
    && chmod 0755 /submission /workspace /srv

WORKDIR /workspace
CMD ["sleep", "infinity"]
