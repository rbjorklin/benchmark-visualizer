.PHONY: build up parse

DB_USER ?= grafana
DB_PASSWORD ?= grafana
COMMIT ?= example
RESULT ?= /mnt/results.csv
JMETER ?= apache-jmeter-5.1.1.tgz

build:
	docker-compose build

up:
	docker-compose up --detach

down:
	docker-compose down

parse:
	docker-compose run parser --file $(RESULT) --user $(DB_USER) --password $(DB_PASSWORD) --commit $(COMMIT)

install-jmeter:
	curl -LOC - http://apache.mirror.rafal.ca//jmeter/binaries/$(JMETER)
	mkdir jmeter
	tar -xzf $(JMETER) --strip-components 1 --directory jmeter

test-example-app:
	# jmeter.reportgenerator.overall_granularity must be greater than 1000
	# https://jmeter.apache.org/usermanual/generating-dashboard.html#configuration_general
	rm -rf output
	jmeter/bin/jmeter --forceDeleteResultFile --nongui \
	    --testfile ./example/testplan.jmx --logfile ./results.csv \
	    --reportatendofloadtests --reportoutputfolder ./output \
	    --jmeterproperty dataFile=./example/requests.csv \
	    --jmeterproperty recycleOnEof=true --jmeterproperty stopOnEof=false \
	    --jmeterproperty jmeter.reportgenerator.overall_granularity 2000
