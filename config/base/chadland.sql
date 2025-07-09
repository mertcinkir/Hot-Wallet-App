--
-- PostgreSQL database dump
--

-- Dumped from database version 14.15 (Ubuntu 14.15-0ubuntu0.22.04.1)
-- Dumped by pg_dump version 14.15 (Ubuntu 14.15-0ubuntu0.22.04.1)

-- Started on 2025-02-21 13:30:19 +03

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = notice;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 220 (class 1259 OID 22177)
-- Name: blockchain; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.blockchain (
    id character varying(8) NOT NULL,
    abbreviation character varying(8) NOT NULL,
    name character varying(32) NOT NULL,
    rpc character varying(128) NOT NULL
);


ALTER TABLE public.blockchain OWNER TO master;

--
-- TOC entry 211 (class 1259 OID 22079)
-- Name: history; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.history (
    id character varying(32) NOT NULL,
    user_id character varying(32) NOT NULL,
    "timestamp" timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    notification_flag boolean NOT NULL,
    operation_flag boolean NOT NULL
);


ALTER TABLE public.history OWNER TO master;

--
-- TOC entry 215 (class 1259 OID 22123)
-- Name: list; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.list (
    id character varying(32) NOT NULL,
    user_id character varying(32) NOT NULL,
    name character varying(32) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.list OWNER TO master;

--
-- TOC entry 210 (class 1259 OID 22067)
-- Name: login; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.login (
    user_id character varying(32) NOT NULL,
    discord_id character varying(32) NOT NULL
);


ALTER TABLE public.login OWNER TO master;

--
-- TOC entry 218 (class 1259 OID 22163)
-- Name: method; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.method (
    signature character varying(8) NOT NULL,
    text character varying(128) NOT NULL,
    keyword character varying(32) NOT NULL,
    abi json NOT NULL
);


ALTER TABLE public.method OWNER TO master;

--
-- TOC entry 212 (class 1259 OID 22090)
-- Name: notification_history; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.notification_history (
    history_id character varying(32) NOT NULL,
    type character varying(32) NOT NULL,
    text character varying(1024) NOT NULL
);


ALTER TABLE public.notification_history OWNER TO master;

--
-- TOC entry 213 (class 1259 OID 22102)
-- Name: operation_history; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.operation_history (
    history_id character varying(32) NOT NULL,
    opcode character varying(64) NOT NULL,
    return character varying(64) NOT NULL
);


ALTER TABLE public.operation_history OWNER TO master;

--
-- TOC entry 216 (class 1259 OID 22137)
-- Name: preference; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.preference (
    user_id character varying(32) NOT NULL,
    primary_wallet_address character varying(64),
    primary_list_id character varying(32),
    discord_notification_flag boolean DEFAULT true
);


ALTER TABLE public.preference OWNER TO master;

--
-- TOC entry 219 (class 1259 OID 22170)
-- Name: protocol; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.protocol (
    id character varying(32) NOT NULL,
    name character varying(32) NOT NULL,
    description character varying(1024) NOT NULL
);


ALTER TABLE public.protocol OWNER TO master;

--
-- TOC entry 221 (class 1259 OID 22182)
-- Name: protocol_instance; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.protocol_instance (
    protocol_id character varying(32) NOT NULL,
    blockchain_id character varying(8) NOT NULL,
    router_address character varying(64) NOT NULL
);


ALTER TABLE public.protocol_instance OWNER TO master;

--
-- TOC entry 222 (class 1259 OID 22199)
-- Name: protocol_methods; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.protocol_methods (
    protocol_id character varying(32) NOT NULL,
    method_signature character varying(8) NOT NULL
);


ALTER TABLE public.protocol_methods OWNER TO master;

--
-- TOC entry 217 (class 1259 OID 22153)
-- Name: tx_history; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.tx_history (
    user_id character varying(32) NOT NULL,
    wallet_address character varying(64) NOT NULL,
    tx_hash character varying(64) NOT NULL,
    description character varying(64) NOT NULL
);


ALTER TABLE public.tx_history OWNER TO master;

--
-- TOC entry 209 (class 1259 OID 22059)
-- Name: user; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public."user" (
    id character varying(32) NOT NULL,
    username character varying(32) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public."user" OWNER TO master;

--
-- TOC entry 214 (class 1259 OID 22112)
-- Name: wallet; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.wallet (
    user_id character varying(32) NOT NULL,
    address character varying(64) NOT NULL,
    pk character varying(128) NOT NULL,
    added_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.wallet OWNER TO master;

--
-- TOC entry 223 (class 1259 OID 22214)
-- Name: wallets_in_list; Type: TABLE; Schema: public; Owner: master
--

CREATE TABLE public.wallets_in_list (
    user_id character varying(32) NOT NULL,
    wallet_address character varying(64) NOT NULL,
    list_id character varying(32) NOT NULL
);


ALTER TABLE public.wallets_in_list OWNER TO master;


--
-- TOC entry 3299 (class 2606 OID 22181)
-- Name: blockchain blockchain_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.blockchain
    ADD CONSTRAINT blockchain_pkey PRIMARY KEY (id);


--
-- TOC entry 3287 (class 2606 OID 22129)
-- Name: list list_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.list
    ADD CONSTRAINT list_pkey PRIMARY KEY (id);


--
-- TOC entry 3289 (class 2606 OID 22131)
-- Name: list list_user_id_name_key; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.list
    ADD CONSTRAINT list_user_id_name_key UNIQUE (user_id, name);


--
-- TOC entry 3295 (class 2606 OID 22169)
-- Name: method method_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.method
    ADD CONSTRAINT method_pkey PRIMARY KEY (signature);


--
-- TOC entry 3281 (class 2606 OID 22096)
-- Name: notification_history notification_history_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.notification_history
    ADD CONSTRAINT notification_history_pkey PRIMARY KEY (history_id);


--
-- TOC entry 3283 (class 2606 OID 22106)
-- Name: operation_history operation_history_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.operation_history
    ADD CONSTRAINT operation_history_pkey PRIMARY KEY (history_id);


--
-- TOC entry 3279 (class 2606 OID 22084)
-- Name: history pk_history_id; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.history
    ADD CONSTRAINT pk_history_id PRIMARY KEY (id);


--
-- TOC entry 3275 (class 2606 OID 22071)
-- Name: login pk_login_user_id; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT pk_login_user_id PRIMARY KEY (user_id);


--
-- TOC entry 3271 (class 2606 OID 22064)
-- Name: user pk_user_id; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT pk_user_id PRIMARY KEY (id);


--
-- TOC entry 3291 (class 2606 OID 22142)
-- Name: preference preference_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.preference
    ADD CONSTRAINT preference_pkey PRIMARY KEY (user_id);


--
-- TOC entry 3301 (class 2606 OID 22186)
-- Name: protocol_instance protocol_instance_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_instance
    ADD CONSTRAINT protocol_instance_pkey PRIMARY KEY (protocol_id, blockchain_id);


--
-- TOC entry 3303 (class 2606 OID 22188)
-- Name: protocol_instance protocol_instance_router_address_key; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_instance
    ADD CONSTRAINT protocol_instance_router_address_key UNIQUE (router_address);


--
-- TOC entry 3305 (class 2606 OID 22203)
-- Name: protocol_methods protocol_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_methods
    ADD CONSTRAINT protocol_methods_pkey PRIMARY KEY (protocol_id, method_signature);


--
-- TOC entry 3297 (class 2606 OID 22176)
-- Name: protocol protocol_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol
    ADD CONSTRAINT protocol_pkey PRIMARY KEY (id);


--
-- TOC entry 3293 (class 2606 OID 22157)
-- Name: tx_history tx_history_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.tx_history
    ADD CONSTRAINT tx_history_pkey PRIMARY KEY (user_id, wallet_address, tx_hash);


--
-- TOC entry 3277 (class 2606 OID 22073)
-- Name: login uk_login_discord_id; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT uk_login_discord_id UNIQUE (discord_id);


--
-- TOC entry 3273 (class 2606 OID 22066)
-- Name: user uk_user_username; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT uk_user_username UNIQUE (username);


--
-- TOC entry 3285 (class 2606 OID 22117)
-- Name: wallet wallet_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.wallet
    ADD CONSTRAINT wallet_pkey PRIMARY KEY (user_id, address);


--
-- TOC entry 3307 (class 2606 OID 22218)
-- Name: wallets_in_list wallets_in_list_pkey; Type: CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.wallets_in_list
    ADD CONSTRAINT wallets_in_list_pkey PRIMARY KEY (user_id, wallet_address, list_id);


--
-- TOC entry 3309 (class 2606 OID 22085)
-- Name: history fk_history_user_id_user_id; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.history
    ADD CONSTRAINT fk_history_user_id_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 3308 (class 2606 OID 22074)
-- Name: login fk_login_user_id_user_id; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.login
    ADD CONSTRAINT fk_login_user_id_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 3313 (class 2606 OID 22132)
-- Name: list list_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.list
    ADD CONSTRAINT list_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 3310 (class 2606 OID 22097)
-- Name: notification_history notification_history_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.notification_history
    ADD CONSTRAINT notification_history_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.history(id);


--
-- TOC entry 3311 (class 2606 OID 22107)
-- Name: operation_history operation_history_history_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.operation_history
    ADD CONSTRAINT operation_history_history_id_fkey FOREIGN KEY (history_id) REFERENCES public.history(id);


--
-- TOC entry 3314 (class 2606 OID 22143)
-- Name: preference preference_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.preference
    ADD CONSTRAINT preference_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 3315 (class 2606 OID 22148)
-- Name: preference preference_user_id_master_wallet_address_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.preference
    ADD CONSTRAINT preference_user_id_primary_wallet_address_fkey FOREIGN KEY (user_id, primary_wallet_address) REFERENCES public.wallet(user_id, address);


--
-- TOC entry 3318 (class 2606 OID 22194)
-- Name: protocol_instance protocol_instance_blockchain_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_instance
    ADD CONSTRAINT protocol_instance_blockchain_id_fkey FOREIGN KEY (blockchain_id) REFERENCES public.blockchain(id);


--
-- TOC entry 3317 (class 2606 OID 22189)
-- Name: protocol_instance protocol_instance_protocol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_instance
    ADD CONSTRAINT protocol_instance_protocol_id_fkey FOREIGN KEY (protocol_id) REFERENCES public.protocol(id);


--
-- TOC entry 3320 (class 2606 OID 22209)
-- Name: protocol_methods protocol_methods_method_signature_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_methods
    ADD CONSTRAINT protocol_methods_method_signature_fkey FOREIGN KEY (method_signature) REFERENCES public.method(signature);


--
-- TOC entry 3319 (class 2606 OID 22204)
-- Name: protocol_methods protocol_methods_protocol_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.protocol_methods
    ADD CONSTRAINT protocol_methods_protocol_id_fkey FOREIGN KEY (protocol_id) REFERENCES public.protocol(id);


--
-- TOC entry 3316 (class 2606 OID 22158)
-- Name: tx_history tx_history_user_id_wallet_address_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.tx_history
    ADD CONSTRAINT tx_history_user_id_wallet_address_fkey FOREIGN KEY (user_id, wallet_address) REFERENCES public.wallet(user_id, address);


--
-- TOC entry 3312 (class 2606 OID 22118)
-- Name: wallet wallet_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.wallet
    ADD CONSTRAINT wallet_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- TOC entry 3322 (class 2606 OID 22224)
-- Name: wallets_in_list wallets_in_list_list_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.wallets_in_list
    ADD CONSTRAINT wallets_in_list_list_id_fkey FOREIGN KEY (list_id) REFERENCES public.list(id);


--
-- TOC entry 3321 (class 2606 OID 22219)
-- Name: wallets_in_list wallets_in_list_user_id_wallet_address_fkey; Type: FK CONSTRAINT; Schema: public; Owner: master
--

ALTER TABLE ONLY public.wallets_in_list
    ADD CONSTRAINT wallets_in_list_user_id_wallet_address_fkey FOREIGN KEY (user_id, wallet_address) REFERENCES public.wallet(user_id, address);


-- Completed on 2025-02-21 13:30:19 +03

--
-- PostgreSQL database dump complete
--