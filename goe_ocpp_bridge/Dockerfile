FROM python:3.12-slim

ARG BUILD_ARCH
ARG BUILD_VERSION

LABEL \
  io.hass.name="go-e v1_v2 OCPP Bridge" \
  io.hass.description="Local go-eCharger HTTP API to OCPP 1.6 JSON bridge" \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /opt/goe-ocpp-bridge

COPY bridge/ /opt/goe-ocpp-bridge/

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .

COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
