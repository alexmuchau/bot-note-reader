import requests

class Notion:
    def __init__(self, notion_api_key: str, database_id: str):
        self.notion_url = "https://api.notion.com/v1"
        self.headers = {
            "Authorization": f"Bearer {notion_api_key}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        self.database_id = database_id
    
    def create_note_page(self, market_name: str, buy_date: str, buy_total: float, items):
        page_id = self._create_note_page(market_name, buy_date, buy_total)
        if page_id is None:
            return False, "Erro na criação da página no notion!"
        
        res = self.insert_items_note_page(page_id, items)
        if res is False:
            return False, "Erro na inserção da tabela de itens no notion!"
        
        return True, "Sucesso na criação da página notion!"
     
    def _create_note_page(self, market_name: str, buy_date: str, buy_total: float):
        body = {
            "parent": {
                "database_id": self.database_id
            },
            "icon": {
                "emoji": "🛒"
            },
            "properties": {
                "Name": {
                    "title": [
                        {
                            "text": {
                                "content": market_name
                            }
                        }
                    ]
                },
                "Date": {
                    "date": {
                        "start": buy_date
                    }
                },
                "Total": {
                    "number": buy_total
                }
            }
        }
        
        create_page_res = requests.post(self.notion_url + '/pages', headers=self.headers, json=body)
    
        if create_page_res.status_code != 200:
            print(create_page_res.json())
            return None
        
        return create_page_res.json()["id"]
    
    def insert_items_note_page(self, page_id: str, items):
        body =  {
            "children": [
                {
                    "object": "block",
                    "type": "table",
                    "table": {
                        "table_width": 2,
                        "has_column_header": False,
                        "has_row_header": True,
                        "children": [
                            {
                                "object": "block",
                                "type": "table_row",
                                "table_row": {
                                    "cells": [
                                        [{"text": {"content": "Item"}}],
                                        [{"text": {"content": "Quantity"}}]
                                    ]
                                }
                            },
                            *[
                                {
                                    "object": "block",
                                    "type": "table_row",
                                    "table_row": {
                                        "cells": [
                                            [{"text": {"content": item["name"]}}],
                                            [{"text": {"content": str(item["qtd"])}}]
                                        ]
                                    }
                                } for item in items.values()
                            ]
                        ]
                    },
                }
            ]
        }
        
        res = requests.patch(self.notion_url + f'/blocks/{page_id}/children', headers=self.headers, json=body)
        
        return res.status_code == 200