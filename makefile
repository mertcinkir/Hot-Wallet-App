.PHONY: up up-detach down down-volumes logs ps ps-all

up:
	docker-compose up

up-detach:
	docker-compose up -d

down:
	docker-compose down

down-volumes:
	docker-compose down -v

logs:
	docker-compose logs -f

ps:
	docker ps

ps-all:
	docker ps -a