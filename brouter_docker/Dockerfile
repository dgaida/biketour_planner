FROM gradle:jdk17-jammy AS build

WORKDIR /tmp/brouter
COPY . .

RUN gradle :brouter-server:fatJar \
    -x checkstyleMain -x checkstyleTest \
    -x pmdMain -x pmdTest

FROM openjdk:17.0.1-jdk-slim

COPY --from=build /tmp/brouter/brouter-server/build/libs/brouter-*-all.jar /brouter.jar
COPY --from=build /tmp/brouter/misc/scripts/standalone/server.sh /server.sh
COPY --from=build /tmp/brouter/misc/* /profiles2

# 🔧 CRLF → LF + ausführbar machen
RUN sed -i 's/\r$//' /server.sh && chmod +x /server.sh

EXPOSE 17777
CMD ["/server.sh"]
