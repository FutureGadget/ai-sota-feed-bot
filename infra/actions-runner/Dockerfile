FROM ghcr.io/actions/actions-runner:2.336.0@sha256:0cfdcc701ce933c6d243c6b0b2da767366dc9f2e99961d4c3754b0b78084cdda

ARG NANUM_COMMIT=16680f8688ffcd467d2eb2146a9ce0343404581d
ARG NANUM_REGULAR_SHA256=76f45ef4a6bcff344c837c95a7dcc26e017e38b5846d5ae0cdcb5b86be2e2d31
ARG NANUM_BOLD_SHA256=21f9d3a7f1ca82ca1dc9a288e30138b4f1feb6e71fc89b5a9181fed174b6bbe2

USER root

RUN install --directory /usr/share/fonts/truetype/nanum \
    && curl --fail --location --show-error \
        --output /usr/share/fonts/truetype/nanum/NanumGothic.ttf \
        "https://raw.githubusercontent.com/google/fonts/${NANUM_COMMIT}/ofl/nanumgothic/NanumGothic-Regular.ttf" \
    && curl --fail --location --show-error \
        --output /usr/share/fonts/truetype/nanum/NanumGothicBold.ttf \
        "https://raw.githubusercontent.com/google/fonts/${NANUM_COMMIT}/ofl/nanumgothic/NanumGothic-Bold.ttf" \
    && printf '%s  %s\n%s  %s\n' \
        "$NANUM_REGULAR_SHA256" /usr/share/fonts/truetype/nanum/NanumGothic.ttf \
        "$NANUM_BOLD_SHA256" /usr/share/fonts/truetype/nanum/NanumGothicBold.ttf \
        | sha256sum --check

COPY --chmod=0755 entrypoint.sh /usr/local/bin/actions-runner-entrypoint

USER runner
WORKDIR /home/runner

ENTRYPOINT ["/usr/local/bin/actions-runner-entrypoint"]
